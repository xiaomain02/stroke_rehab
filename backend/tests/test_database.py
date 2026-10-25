from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import configure_mappers

from app.config import BACKEND_ROOT, get_settings
from scripts.seed import seed

SQL = (BACKEND_ROOT / "scripts/init.sql").read_text()


def alembic_config():
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    monkeypatch.setenv("DATABASE_URL_SYNC", f"sqlite:///{path}")
    monkeypatch.setenv("SEED_DEMO_PASSWORD", "TestDemo123!")
    get_settings.cache_clear()
    yield path
    get_settings.cache_clear()


def migrate():
    command.upgrade(alembic_config(), "head")


async def populate(path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_fk(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            async with session.begin():
                return await seed(session)
    finally:
        await engine.dispose()


@pytest.fixture
def populated(db_path):
    migrate()
    asyncio.run(populate(db_path))
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        yield connection


def test_models_configure_without_name_shadowing():
    configure_mappers()


def test_raw_init_sql_is_complete():
    with sqlite3.connect(":memory:") as connection:
        connection.executescript(SQL)
        assert connection.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0] == 9
        assert connection.execute("SELECT * FROM attempt_results").fetchall() == []
        assert connection.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0] == 1


def test_migration_is_repeatable_and_models_match(db_path):
    migrate()
    migrate()
    command.check(alembic_config())
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0001_initial"


def test_adopts_legacy_database_without_losing_rows(db_path):
    with sqlite3.connect(db_path) as connection:
        connection.executescript(SQL[:SQL.index("CREATE TRIGGER")])
        connection.execute("INSERT INTO users(email,password_hash,full_name,role) VALUES ('sentinel@example.test','hash','Fixture','patient')")
    migrate()
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT count(*) FROM users").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM sqlite_master WHERE type IN ('trigger','view')").fetchone()[0] == 2
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_refuses_unrecognized_database_without_creating_partial_schema(db_path):
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE unrelated (id INTEGER)")
    before = db_path.read_bytes()
    with pytest.raises(RuntimeError, match="unknown set of tables"):
        migrate()
    assert db_path.read_bytes() == before


def test_refuses_changed_legacy_table(db_path):
    with sqlite3.connect(db_path) as connection:
        connection.executescript(SQL[:SQL.index("CREATE TRIGGER")])
        connection.execute("ALTER TABLE users ADD COLUMN surprise TEXT")
    before = db_path.read_bytes()
    with pytest.raises(RuntimeError, match="differs"):
        migrate()
    assert db_path.read_bytes() == before


def test_seed_is_idempotent_and_creates_no_fake_media(populated, db_path):
    def counts():
        return {table: populated.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("users", "doctor_profiles", "patient_profiles", "doctor_patients", "exercises", "assignments", "attempts", "diary_entries", "media_files")}
    before = counts()
    asyncio.run(populate(db_path))
    assert counts() == before == {"users": 7, "doctor_profiles": 2, "patient_profiles": 5,
        "doctor_patients": 5, "exercises": 4, "assignments": 10, "attempts": 20,
        "diary_entries": 15, "media_files": 0}
    assert populated.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("case", [
    "email_case", "profile_role", "diary_duplicate", "media_both_targets", "media_no_target",
    "media_wrong_type", "media_wrong_mime", "media_zero_size", "media_bad_status",
    "attempt_missing_assignment", "attempt_score", "attempt_submission_duplicate",
    "exercise_config_array", "attempt_invalid_json", "assignment_config_array",
])
def test_integrity_constraints(populated, case):
    connection = populated
    email = connection.execute("SELECT email FROM users LIMIT 1").fetchone()[0]
    doctor_id = connection.execute("SELECT user_id FROM doctor_profiles LIMIT 1").fetchone()[0]
    patient_id = connection.execute("SELECT user_id FROM patient_profiles LIMIT 1").fetchone()[0]
    attempt_id, assignment_id = connection.execute("SELECT id,assignment_id FROM attempts LIMIT 1").fetchone()
    exercise_id = connection.execute("SELECT id FROM exercises LIMIT 1").fetchone()[0]
    media = dict(uploaded_by=doctor_id, exercise_id=exercise_id, attempt_id=None,
                 media_type="video", storage_key="tests/not-a-real-upload.webm",
                 original_name="answer.webm", mime_type="video/webm", size_bytes=100, status="pending")
    with pytest.raises(sqlite3.IntegrityError):
        if case == "email_case":
            connection.execute("INSERT INTO users(email,password_hash,full_name,role) VALUES (?,'hash','Fixture','doctor')", (email.upper(),))
        elif case == "profile_role":
            connection.execute("INSERT INTO doctor_profiles(user_id,role) VALUES (?,'doctor')", (patient_id,))
        elif case == "diary_duplicate":
            connection.execute("INSERT INTO diary_entries(patient_id,entry_date,wellbeing) SELECT patient_id,entry_date,3 FROM diary_entries LIMIT 1")
        elif case.startswith("media_"):
            if case == "media_both_targets": media["attempt_id"] = attempt_id
            if case == "media_no_target": media["exercise_id"] = None
            if case == "media_wrong_type": media["media_type"] = "image"
            if case == "media_wrong_mime": media["mime_type"] = "audio/webm"
            if case == "media_zero_size": media["size_bytes"] = 0
            if case == "media_bad_status": media["status"] = "uploaded"
            columns = ",".join(media)
            connection.execute(f"INSERT INTO media_files({columns}) VALUES ({','.join('?' for _ in media)})", tuple(media.values()))
        elif case == "attempt_missing_assignment":
            connection.execute("UPDATE attempts SET assignment_id=-123 WHERE id=?", (attempt_id,))
        elif case == "attempt_score":
            connection.execute("UPDATE attempts SET auto_score=101 WHERE id=?", (attempt_id,))
        elif case == "attempt_submission_duplicate":
            connection.execute("UPDATE attempts SET submission_key=(SELECT submission_key FROM attempts WHERE id=?) WHERE id != ?", (attempt_id, attempt_id))
        elif case == "exercise_config_array":
            connection.execute("UPDATE exercises SET default_config='[]' WHERE id=?", (exercise_id,))
        elif case == "attempt_invalid_json":
            connection.execute("UPDATE attempts SET raw_result='invalid' WHERE id=?", (attempt_id,))
        elif case == "assignment_config_array":
            connection.execute("UPDATE assignments SET config_snapshot='[]' WHERE id=?", (assignment_id,))


def test_diary_trigger_updates_only_edited_row_and_does_not_recurse(populated):
    populated.execute("PRAGMA recursive_triggers=ON")
    ids = [row[0] for row in populated.execute("SELECT id FROM diary_entries ORDER BY id LIMIT 2")]
    populated.execute("UPDATE diary_entries SET updated_at='2000-01-01T00:00:00Z' WHERE id IN (?,?)", ids)
    populated.execute("UPDATE diary_entries SET note='Changed' WHERE id=?", (ids[0],))
    rows = populated.execute("SELECT updated_at FROM diary_entries WHERE id IN (?,?) ORDER BY id", ids).fetchall()
    assert rows[0][0] != '2000-01-01T00:00:00Z'
    assert rows[1][0] == '2000-01-01T00:00:00Z'


def test_effective_score_preserves_zero_and_doctor_priority(populated):
    attempt_id = populated.execute("SELECT id FROM attempts LIMIT 1").fetchone()[0]
    doctor_id = populated.execute("SELECT user_id FROM doctor_profiles LIMIT 1").fetchone()[0]
    populated.execute("UPDATE attempts SET auto_score=75,doctor_score=0,reviewed_by=?,reviewed_at='2026-01-01T12:00:00Z' WHERE id=?", (doctor_id, attempt_id))
    assert populated.execute("SELECT effective_score FROM attempt_results WHERE attempt_id=?", (attempt_id,)).fetchone()[0] == 0


def test_historical_doctor_link_does_not_block_a_new_active_link(populated):
    link_id, doctor_id, patient_id = populated.execute("SELECT id,doctor_id,patient_id FROM doctor_patients LIMIT 1").fetchone()
    with pytest.raises(sqlite3.IntegrityError):
        populated.execute("INSERT INTO doctor_patients(doctor_id,patient_id) VALUES (?,?)", (doctor_id, patient_id))
    populated.execute("UPDATE doctor_patients SET ended_at='2099-01-01T00:00:00Z' WHERE id=?", (link_id,))
    populated.execute("INSERT INTO doctor_patients(doctor_id,patient_id) VALUES (?,?)", (doctor_id, patient_id))


def test_settings_reject_two_different_database_files(db_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL_SYNC", f"sqlite:///{db_path.parent / 'other.db'}")
    with pytest.raises(ValueError, match="same SQLite file"):
        get_settings()


def test_relative_database_path_is_anchored_to_backend(db_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./data/test.db")
    monkeypatch.setenv("DATABASE_URL_SYNC", "sqlite:///./data/test.db")
    monkeypatch.chdir(db_path.parent)
    assert str(BACKEND_ROOT / 'data/test.db') in get_settings().DATABASE_URL


def test_backup_is_consistent_and_never_overwrites(db_path, tmp_path):
    from scripts.backup_db import backup_database
    migrate()
    destination = tmp_path / 'backups/snapshot.db'
    original_bytes = db_path.read_bytes()
    backup_database(db_path, destination)
    assert db_path.read_bytes() == original_bytes
    with sqlite3.connect(destination) as connection:
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone()[0] == '0001_initial'
    with pytest.raises(FileExistsError):
        backup_database(db_path, destination)
    with pytest.raises(FileExistsError):
        backup_database(db_path, db_path)
    assert db_path.read_bytes() == original_bytes


def test_check_db_reports_missing_legacy_objects_without_writing(db_path, capsys):
    from scripts.check_db import main
    with sqlite3.connect(db_path) as connection:
        connection.executescript(SQL[:SQL.index('CREATE TRIGGER')])
    original_bytes = db_path.read_bytes()
    assert main() == 1
    assert 'Incomplete schema' in capsys.readouterr().out
    assert db_path.read_bytes() == original_bytes


def test_check_db_after_migration(db_path, capsys):
    from scripts.check_db import main
    migrate()
    assert main() == 0
    assert 'Schema, integrity and foreign keys: OK' in capsys.readouterr().out


def test_timestamp_type_preserves_utc_and_rejects_naive_values():
    from datetime import datetime, timedelta, timezone
    from app.db.types import UTCDateTime
    field = UTCDateTime()
    local = datetime(2026, 10, 25, 15, 30, 0, 123456, tzinfo=timezone(timedelta(hours=3)))
    encoded = field.process_bind_param(local, None)
    assert encoded == '2026-10-25T12:30:00.123Z'
    assert field.process_result_value(encoded, None).utcoffset() == timedelta(0)
    with pytest.raises(ValueError, match='timezone-aware'):
        field.process_bind_param(datetime(2026, 10, 25), None)


def test_can_end_a_relationship_created_by_sql_on_the_same_day(populated, db_path):
    from datetime import datetime, timedelta, timezone
    from app.db.models import DoctorPatient
    doctor = populated.execute('SELECT user_id FROM doctor_profiles ORDER BY user_id LIMIT 1').fetchone()[0]
    patient = populated.execute('SELECT user_id FROM patient_profiles ORDER BY user_id LIMIT 1 OFFSET 1').fetchone()[0]
    cursor = populated.execute('INSERT INTO doctor_patients(doctor_id,patient_id) VALUES (?,?)', (doctor, patient))
    link_id = cursor.lastrowid
    populated.commit()

    async def end_link():
        engine = create_async_engine(f'sqlite+aiosqlite:///{db_path}')
        try:
            async with async_sessionmaker(engine)() as session:
                async with session.begin():
                    link = await session.get(DoctorPatient, link_id)
                    assert link.started_at.utcoffset() == timedelta(0)
                    link.ended_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        finally:
            await engine.dispose()
    asyncio.run(end_link())
    assert populated.execute('SELECT ended_at FROM doctor_patients WHERE id=?', (link_id,)).fetchone()[0].endswith('Z')
