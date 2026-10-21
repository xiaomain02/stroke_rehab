"""Shared patient progress calculations."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta, timezone


def week_start() -> datetime:
    today = datetime.now(timezone.utc).date()
    return datetime.combine(today - timedelta(days=today.weekday()), time.min, timezone.utc)


def assignment_progress(db: sqlite3.Connection, assignment: sqlite3.Row) -> tuple[str, int]:
    count = db.execute(
        "SELECT COUNT(*) FROM results WHERE assignment_id = ? AND created_at >= ?",
        (assignment["id"], week_start().isoformat()),
    ).fetchone()[0]
    if count >= assignment["times_per_week"]:
        return "done", count
    if assignment["due_date"] and date.fromisoformat(assignment["due_date"]) < datetime.now(timezone.utc).date():
        return "overdue", count
    return ("in_progress" if count else "new"), count


def patient_stats(db: sqlite3.Connection, patient_id: int) -> dict:
    scores = [row[0] for row in db.execute(
        "SELECT score FROM results WHERE patient_id = ? ORDER BY created_at DESC, id DESC LIMIT 10",
        (patient_id,),
    )]
    all_average = db.execute("SELECT AVG(score), COUNT(*) FROM results WHERE patient_id = ?", (patient_id,)).fetchone()
    total_assignments = db.execute("SELECT COUNT(*) FROM assignments WHERE patient_id = ?", (patient_id,)).fetchone()[0]
    done = 0
    for assignment in db.execute("SELECT * FROM assignments WHERE patient_id = ?", (patient_id,)):
        status, _ = assignment_progress(db, assignment)
        done += status == "done"
    previous = sum(scores[5:10]) / 5 if len(scores) == 10 else None
    recent = sum(scores[:5]) / min(5, len(scores)) if scores else None
    trend = ((recent - previous) / previous * 100) if previous not in (None, 0) and recent is not None and len(scores) == 10 else 0.0
    return {
        "avg_score": all_average[0],
        "trend": trend,
        "sessions_total": all_average[1],
        "completion_rate": done / total_assignments * 100 if total_assignments else 0.0,
    }
