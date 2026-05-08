"""
Module 8 Student Enrollment backend starter.

This file is intentionally procedural. It has functions and top-level
database code, but no classes yet. Students will first group related behavior
into an EnrollmentManager class, then separate service and database layers.

App idea:
    - a student opens a dashboard
    - the dashboard shows enrolled classes
    - the student enters an enrollment key to join another class
    - the database stores courses and enrollment records
    - a JSON snapshot is exported so students can inspect the seeded data

Focus:
    - student enrollment behavior
    - local SQLite database
    - enrollment keys
    - soft unenroll using status = "unenrolled"

Out of scope:
    - Streamlit UI
    - authentication/session state
    - caching
    - export formatting
    - production health checks

Run with:
    enrollment_starter.py
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional


DB_PATH = Path(__file__).with_name("student_enrollment_practice.db")
SNAPSHOT_PATH = Path(__file__).with_name("student_enrollment_snapshot.json")

CURRENT_STUDENT = {
    "user_id": "u100",
    "name": "Maya Patel",
    "email": "maya.patel@example.edu",
}

STATUS_ENROLLED = "enrolled"
STATUS_UNENROLLED = "unenrolled"

AVAILABLE_COURSE_KEYS = [
    {
        "course_id": "MISY350",
        "course_name": "Python for Business Analytics",
        "instructor": "Dr. Rivera",
        "enrollment_key": "MISY350-SPRING",
    },
    {
        "course_id": "DATA210",
        "course_name": "Data Storytelling",
        "instructor": "Prof. Morgan",
        "enrollment_key": "DATA210-SPRING",
    },
    {
        "course_id": "WEB220",
        "course_name": "Web Apps With Streamlit",
        "instructor": "Dr. Chen",
        "enrollment_key": "WEB220-SPRING",
    },
]

SAMPLE_ENROLLMENTS = [
    ("u100", "maya.patel@example.edu", "MISY350", STATUS_ENROLLED),
    ("u100", "maya.patel@example.edu", "DATA210", STATUS_UNENROLLED),
    ("u101", "alex@example.edu", "MISY350", STATUS_ENROLLED),
    ("u102", "blair@example.edu", "WEB220", STATUS_ENROLLED),
]


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        """Open a database connection."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create_tables(self) -> None:
        """Create the courses and enrollments tables."""
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS courses (
                    course_id TEXT PRIMARY KEY,
                    course_name TEXT NOT NULL,
                    instructor TEXT NOT NULL,
                    enrollment_key TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS enrollments (
                    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'enrolled',
                    enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, course_id),
                    FOREIGN KEY(course_id) REFERENCES courses(course_id)
                )
                """
            )

    def seed_sample_data(self) -> None:
        """Seed courses, enrollment keys, and a few practice enrollment records."""
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO courses (
                    course_id, course_name, instructor, enrollment_key
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        course["course_id"],
                        course["course_name"],
                        course["instructor"],
                        course["enrollment_key"],
                    )
                    for course in AVAILABLE_COURSE_KEYS
                ],
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO enrollments (user_id, email, course_id, status)
                VALUES (?, ?, ?, ?)
                """,
                SAMPLE_ENROLLMENTS,
            )

    def get_available_course_keys(self) -> list[dict[str, Any]]:
        """Return the course keys that a UI could show for practice."""
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                ORDER BY course_id
                """
            ).fetchall()

        return self.rows_to_dicts(rows)

    def get_course_by_key(self, enrollment_key: str) -> Optional[dict[str, Any]]:
        """Find a course by its enrollment key."""
        if not enrollment_key:
            return None

        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                WHERE enrollment_key = ?
                """,
                (enrollment_key.strip().upper(),),
            ).fetchone()

        return dict(row) if row else None

    def get_student_enrollments(self, user_id: str) -> list[dict[str, Any]]:
        """Return the classes where the student is currently enrolled."""
        if not user_id:
            return []

        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ? AND e.status = ?
                ORDER BY c.course_id
                """,
                (user_id, STATUS_ENROLLED),
            ).fetchall()

        return self.rows_to_dicts(rows)

    def get_student_enrollment_history(self, user_id: str) -> list[dict[str, Any]]:
        """Return all enrollment records for one student, including unenrolled."""
        if not user_id:
            return []

        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ?
                ORDER BY c.course_id
                """,
                (user_id,),
            ).fetchall()

        return self.rows_to_dicts(rows)

    def get_student_course_record(
        self,
        user_id: str,
        course_id: str,
    ) -> Optional[dict[str, Any]]:
        """Return one student's enrollment record for one course."""
        if not user_id or not course_id:
            return None

        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT enrollment_id, user_id, email, course_id, status, enrolled_at
                FROM enrollments
                WHERE user_id = ? AND course_id = ?
                """,
                (user_id, course_id),
            ).fetchone()

        return dict(row) if row else None

    def enroll_student(
        self,
        user_id: str,
        email: str,
        course_id: str,
    ) -> Optional[dict[str, Any]]:
        """Enroll or reactivate a student in a course."""
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO enrollments (user_id, email, course_id, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, course_id)
                DO UPDATE SET
                    email = excluded.email,
                    status = excluded.status,
                    enrolled_at = CURRENT_TIMESTAMP
                """,
                (user_id, email, course_id, STATUS_ENROLLED),
            )

        return self.get_student_course_record(user_id, course_id)

    def soft_unenroll_student(self, user_id: str, course_id: str) -> bool:
        """Soft-unenroll one student by changing status instead of deleting."""
        if not user_id or not course_id:
            return False

        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE enrollments
                SET status = ?
                WHERE user_id = ? AND course_id = ?
                """,
                (STATUS_UNENROLLED, user_id, course_id),
            )

        return cursor.rowcount > 0

    def get_all_enrollment_records(self) -> list[dict[str, Any]]:
        """Return every enrollment record for the database snapshot."""
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                ORDER BY e.user_id, e.course_id
                """
            ).fetchall()

        return self.rows_to_dicts(rows)

    @staticmethod
    def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        """Convert SQLite rows into dictionaries."""
        return [dict(row) for row in rows]


class EnrollmentService:
    def __init__(self, database: Database):
        self.database = database

    def get_student_enrollments(self, user_id: str) -> list[dict[str, Any]]:
        """Return active enrollment records for one student."""
        return self.database.get_student_enrollments(user_id)

    def get_student_enrollment_history(self, user_id: str) -> list[dict[str, Any]]:
        """Return all enrollment records for one student."""
        return self.database.get_student_enrollment_history(user_id)

    def get_student_course_record(
        self,
        user_id: str,
        course_id: str,
    ) -> Optional[dict[str, Any]]:
        """Return one student's enrollment record for one course."""
        return self.database.get_student_course_record(user_id, course_id)

    def enroll_with_key(
        self,
        user_id: str,
        email: str,
        enrollment_key: str,
    ) -> Optional[dict[str, Any]]:
        """Enroll or reactivate a student using a course enrollment key."""
        if not user_id or not email or "@" not in email or not enrollment_key:
            return None

        course = self.database.get_course_by_key(enrollment_key)
        if not course:
            return None

        return self.database.enroll_student(user_id, email, course["course_id"])

    def soft_unenroll_student(self, user_id: str, course_id: str) -> bool:
        """Soft-unenroll one student by changing status instead of deleting."""
        if not user_id or not course_id:
            return False

        return self.database.soft_unenroll_student(user_id, course_id)

    def get_student_summary(self, user_id: str) -> dict[str, int]:
        """Return summary counts for one student."""
        summary = {
            "total_records": 0,
            STATUS_ENROLLED: 0,
            STATUS_UNENROLLED: 0,
        }

        for record in self.database.get_student_enrollment_history(user_id):
            summary["total_records"] += 1
            status = record["status"]
            if status in summary:
                summary[status] += 1

        return summary

    def export_database_snapshot(self, path: Path = SNAPSHOT_PATH) -> None:
        """Write seeded database content to JSON so students can inspect it."""
        snapshot = {
            "current_student": CURRENT_STUDENT,
            "available_course_keys": self.database.get_available_course_keys(),
            "enrollment_table": self.database.get_all_enrollment_records(),
        }
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def main() -> None:
    """Small terminal runner for checking behavior before the UI exists."""
    database = Database(DB_PATH)
    database.create_tables()
    database.seed_sample_data()

    service = EnrollmentService(database)

    user_id = CURRENT_STUDENT["user_id"]
    email = CURRENT_STUDENT["email"]

    print("Current student:")
    print(CURRENT_STUDENT)

    print("\nAvailable enrollment keys:")
    print(database.get_available_course_keys())

    print("\nInitial enrolled classes:")
    print(database.get_student_enrollments(user_id))

    print("\nStudent enters key DATA210-SPRING:")
    print(service.enroll_with_key(user_id, email, "DATA210-SPRING"))

    print("\nUpdated enrolled classes:")
    print(database.get_student_enrollments(user_id))

    print("\nStudent summary:")
    print(service.get_student_summary(user_id))

    service.export_database_snapshot()
    print(f"\nDatabase snapshot written to: {SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()
