"""Idempotent synthetic DB fixtures. Never uploads files or contacts Object Storage."""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Assignment, Attempt, DiaryEntry, DoctorPatient, DoctorProfile,
    Exercise, PatientProfile, User,
)

DEMO_MARKER = "[demo-seed-v1]"
DEMO_PASSWORD = "DemoPass123!"  # Public fixture only, never use for real accounts.
EXERCISES = (
    ("target_click", "Нажатие на цели", "motor", {"target_count": 10, "time_limit_seconds": 60}),
    ("repeat_phrase", "Повторение фразы", "speech", {"phrase": "Сегодня хорошая погода"}),
    ("memory_pairs", "Парные карточки", "memory", {"pairs": 4}),
    ("sequence_recall", "Повторение последовательности", "memory", {"length": 4}),
)


async def seed(session: AsyncSession) -> dict[str, int]:
    password = os.environ.get("SEED_DEMO_PASSWORD", DEMO_PASSWORD)
    if not password or len(password.encode("utf-8")) > 72:
        raise ValueError("SEED_DEMO_PASSWORD must contain 1–72 UTF-8 bytes for bcrypt.")
    password_hash = None
    doctors, patients = [], []
    for role, total in (("doctor", 2), ("patient", 5)):
        for number in range(1, total + 1):
            email = f"{role}{number}@example.test"
            user = await session.scalar(select(User).where(func.lower(User.email) == email))
            if user is None:
                if password_hash is None:
                    password_hash = await asyncio.to_thread(CryptContext(schemes=["bcrypt"]).hash, password)
                user = User(email=email, password_hash=password_hash,
                            full_name=f"Demo {role} {number}", role=role)
                session.add(user)
                await session.flush()
            elif user.role != role:
                raise ValueError("A reserved demo email belongs to an account with another role.")
            profile_class = DoctorProfile if role == "doctor" else PatientProfile
            if await session.get(profile_class, user.id) is None:
                session.add(profile_class(user_id=user.id, role=role))
                await session.flush()
            (doctors if role == "doctor" else patients).append(user)

    exercises = []
    for code, title, category, config in EXERCISES:
        exercise = await session.scalar(select(Exercise).where(Exercise.code == code))
        if exercise is None:
            exercise = Exercise(code=code, title=title, description="Синтетическое упражнение для демонстрации.",
                                category=category, component_key=code, default_config=config,
                                scoring_version="v1", created_by=doctors[0].id)
            session.add(exercise)
            await session.flush()
        exercises.append(exercise)

    today = datetime.now(timezone.utc).date()
    demo_attempts = 0
    for i, patient in enumerate(patients):
        doctor = doctors[i % len(doctors)]
        link = await session.scalar(select(DoctorPatient).where(
            DoctorPatient.doctor_id == doctor.id,
            DoctorPatient.patient_id == patient.id,
            DoctorPatient.ended_at.is_(None),
        ))
        if link is None:
            link = DoctorPatient(doctor_id=doctor.id, patient_id=patient.id,
                                 started_at=datetime.combine(today - timedelta(days=14), time(), timezone.utc))
            session.add(link)
            await session.flush()
        for j in range(2):
            exercise = exercises[(i + j) % len(exercises)]
            assignment = await session.scalar(select(Assignment).where(
                Assignment.doctor_patient_id == link.id,
                Assignment.exercise_id == exercise.id,
                Assignment.doctor_note == DEMO_MARKER,
            ))
            if assignment is None:
                assignment = Assignment(
                    doctor_patient_id=link.id, exercise_id=exercise.id,
                    starts_on=today - timedelta(days=14), ends_on=today + timedelta(days=14),
                    target_attempts=2, status="completed", doctor_note=DEMO_MARKER,
                    config_snapshot=dict(exercise.default_config), scoring_version=exercise.scoring_version,
                )
                session.add(assignment)
                await session.flush()
            for n in range(2):
                submission_key = str(uuid.uuid5(uuid.NAMESPACE_URL,
                    f"stroke-rehab-demo-v1/patient/{i + 1}/{exercise.code}/attempt/{n + 1}"))
                attempt = await session.scalar(select(Attempt).where(Attempt.submission_key == submission_key))
                if attempt is None:
                    started = datetime.combine(assignment.starts_on + timedelta(days=n + 1), time(10), timezone.utc)
                    speech = exercise.category == "speech"
                    reviewed = speech and n == 1
                    attempt = Attempt(
                        assignment_id=assignment.id, submission_key=submission_key,
                        started_at=started, completed_at=started + timedelta(seconds=30 + n * 5),
                        duration_ms=(30 + n * 5) * 1000,
                        auto_score=None if speech else 65 + i + n * 10,
                        doctor_score=80 if reviewed else None,
                        raw_result={"demo": True, "exercise": exercise.code, "attempt_number": n + 1},
                        reviewed_by=doctor.id if reviewed else None,
                        reviewed_at=started + timedelta(hours=1) if reviewed else None,
                        doctor_feedback="Демонстрационная оценка" if reviewed else None,
                    )
                    session.add(attempt)
                    await session.flush()
                demo_attempts += 1
        # Fixed relative to the seeded assignments, so re-running tomorrow adds no diary duplicates.
        diary_base = await session.scalar(select(func.min(Assignment.starts_on)).where(
            Assignment.doctor_patient_id == link.id, Assignment.doctor_note == DEMO_MARKER,
        ))
        for offset in range(3):
            entry_day = diary_base + timedelta(days=offset + 1)
            existing = await session.scalar(select(DiaryEntry.id).where(
                DiaryEntry.patient_id == patient.id, DiaryEntry.entry_date == entry_day,
            ))
            if existing is None:
                session.add(DiaryEntry(patient_id=patient.id, entry_date=entry_day,
                    wellbeing=3 + offset % 2, mood=3, fatigue=4 - offset, note=DEMO_MARKER))
    await session.flush()
    return {"demo_doctors": len(doctors), "demo_patients": len(patients),
            "demo_exercises": len(exercises), "demo_attempts": demo_attempts}


async def main() -> None:
    from app.db.session import SessionLocal, engine
    try:
        async with SessionLocal() as session:
            async with session.begin():
                summary = await seed(session)
        print("Demo data ready: " + ", ".join(f"{key}={value}" for key, value in summary.items()))
        print("Media files were not created: real uploads belong to the backend storage flow.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
