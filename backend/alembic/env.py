from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import Boolean, Date, DateTime, Integer, JSON, String, Table, Text, engine_from_config, event, pool
from sqlalchemy.engine import make_url

from app.config import get_settings
from app.db.base import Base
import app.db.models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC.replace("%", "%%"))

target_metadata = Base.metadata


@event.listens_for(Table, "column_reflect")
def sqlite_integer_primary_key_is_not_null(inspector, table, column_info):
    # PRAGMA table_info reports nullable=True for INTEGER PRIMARY KEY, although
    # SQLite generates an integer rowid on NULL inserts; it never stores NULL.
    if inspector.dialect.name == "sqlite" and isinstance(column_info["type"], Integer):
        primary_key = inspector.get_pk_constraint(table.name).get("constrained_columns", [])
        if len(primary_key) == 1 and column_info["name"] in primary_key:
            column_info["nullable"] = False


def compare_sqlite_type(context, inspected_column, metadata_column, inspected_type, metadata_type):
    # SQLite's canonical SQL uses TEXT for dates, JSON and strings. ORM uses
    # typed serializers on those same TEXT columns; this is intentional.
    if context.dialect.name == "sqlite":
        if isinstance(inspected_type, Text) and isinstance(metadata_type, (String, Date, DateTime, JSON)):
            return False
        if (inspected_column.name == "is_active"
                and isinstance(inspected_type, Integer) and isinstance(metadata_type, Boolean)):
            return False  # INTEGER + CHECK(0,1), exposed as bool by the ORM.
    return None


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=compare_sqlite_type,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    Path(make_url(settings.DATABASE_URL_SYNC).database).parent.mkdir(parents=True, exist_ok=True)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    @event.listens_for(connectable, "connect")
    def prepare_sqlite(dbapi_connection, _):
        dbapi_connection.isolation_level = None
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    @event.listens_for(connectable, "begin")
    def begin_sqlite(connection):
        connection.exec_driver_sql("BEGIN")

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=compare_sqlite_type,
            transactional_ddl=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
