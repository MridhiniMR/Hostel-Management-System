"""Small local administration CLI; passwords are prompted, not echoed or stored in source."""
from __future__ import annotations

import argparse
from getpass import getpass

from sqlalchemy import select

from hms.database import Base, SessionLocal, engine
from hms import models  # noqa: F401
from hms.models import Student, User
from hms.security import hash_password
from hms.services import create_user


def main() -> None:
    parser = argparse.ArgumentParser(description="Hostel Management System local administration")
    sub = parser.add_subparsers(dest="command", required=True)
    create_user_parser = sub.add_parser("create-user", help="Create an administrator or student login")
    create_user_parser.add_argument("--username", required=True)
    create_user_parser.add_argument("--role", choices=["ADMIN", "STUDENT"], default="STUDENT")
    create_user_parser.add_argument("--student-id", help="Link a STUDENT account to an existing student record")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    password = getpass("Password (minimum 10 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        parser.error("Passwords do not match.")
    if args.student_id and args.role != "STUDENT":
        parser.error("--student-id can only be used with --role STUDENT.")
    db = SessionLocal()
    try:
        user = create_user(db, args.username, password, args.role)
        if args.student_id:
            student = db.scalar(select(Student).where(Student.student_id == args.student_id))
            if student is None:
                db.delete(user)
                db.commit()
                parser.error("That student record does not exist yet. Create it in the admin interface first.")
            if student.account_user_id is not None:
                db.delete(user)
                db.commit()
                parser.error("That student record already has a linked account.")
            student.account_user_id = user.id
            db.commit()
        print(f"Created {user.role} account '{user.username}'.")
    except ValueError as exc:
        parser.error(str(exc))
    finally:
        db.close()


if __name__ == "__main__":
    main()
