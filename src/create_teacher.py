"""Create a teacher account for the local activities application."""

import getpass
import json
import os

from src.app import TEACHERS_FILE, hash_password


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username or len(username) > 128:
        raise SystemExit("Username must contain between 1 and 128 characters.")

    password = getpass.getpass("Teacher password: ")
    if not password or len(password) > 256:
        raise SystemExit("Password must contain between 1 and 256 characters.")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")

    try:
        teachers = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        teachers = []
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SystemExit(f"Cannot read {TEACHERS_FILE}: expected UTF-8 JSON.") from error

    if not isinstance(teachers, list) or any(
        not isinstance(teacher, dict)
        or not isinstance(teacher.get("username"), str)
        for teacher in teachers
    ):
        raise SystemExit(f"Cannot read {TEACHERS_FILE}: invalid teacher account format.")
    if any(teacher["username"] == username for teacher in teachers):
        raise SystemExit(f"Teacher account {username!r} already exists.")

    salt, password_hash = hash_password(password)
    teachers.append(
        {"username": username, "salt": salt, "password_hash": password_hash}
    )

    TEACHERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        TEACHERS_FILE,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        json.dump(teachers, file, indent=2)
        file.write("\n")
    print(f"Teacher account {username!r} created.")


if __name__ == "__main__":
    main()
