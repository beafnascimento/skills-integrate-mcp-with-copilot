"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

PASSWORD_HASH_ITERATIONS = 310_000
TEACHERS_FILE = current_dir / "teachers.json"
SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(32)
DUMMY_SALT = bytes(16)
DUMMY_PASSWORD_HASH = hashlib.pbkdf2_hmac(
    "sha256", b"not-a-teacher-password", DUMMY_SALT, PASSWORD_HASH_ITERATIONS
)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=8 * 60 * 60,
    same_site="lax",
    https_only=os.environ.get("HTTPS_ONLY", "").lower() == "true",
)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return salt.hex(), password_hash.hex()


def get_teacher_records() -> list[dict[str, str]]:
    try:
        records = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=503,
            detail="Teacher accounts are not configured. Run `python -m src.create_teacher`.",
        ) from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise HTTPException(
            status_code=503,
            detail="Teacher accounts file is not valid UTF-8 JSON.",
        ) from error

    if not isinstance(records, list) or any(
        not isinstance(record, dict)
        or not all(
            isinstance(record.get(key), str)
            for key in ("username", "salt", "password_hash")
        )
        for record in records
    ):
        raise HTTPException(
            status_code=503,
            detail="Teacher accounts file has an invalid format.",
        )
    return records


def is_valid_teacher(username: str, password: str) -> bool:
    records = get_teacher_records()
    teacher = next(
        (record for record in records if record["username"] == username),
        None,
    )
    try:
        salt = bytes.fromhex(teacher["salt"]) if teacher else DUMMY_SALT
        expected_hash = (
            bytes.fromhex(teacher["password_hash"])
            if teacher
            else DUMMY_PASSWORD_HASH
        )
    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail="Teacher accounts file has an invalid password hash.",
        ) from error
    if teacher and (len(salt) != 16 or len(expected_hash) != 32):
        raise HTTPException(
            status_code=503,
            detail="Teacher accounts file has an invalid password hash.",
        )
    _, actual_hash = hash_password(password, salt)
    password_matches = hmac.compare_digest(bytes.fromhex(actual_hash), expected_hash)
    return teacher is not None and password_matches


def require_teacher(request: Request) -> None:
    if not request.session.get("teacher"):
        raise HTTPException(status_code=401, detail="Teacher login required")


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/session")
def get_session(request: Request):
    teacher = request.session.get("teacher")
    return {"authenticated": bool(teacher), "username": teacher}


@app.post("/auth/login")
def login(credentials: LoginRequest, request: Request):
    if not is_valid_teacher(credentials.username, credentials.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    request.session.clear()
    request.session["teacher"] = credentials.username
    return {"message": "Logged in successfully", "username": credentials.username}


@app.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, request: Request):
    """Sign up a student for an activity"""
    require_teacher(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, request: Request):
    """Unregister a student from an activity"""
    require_teacher(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
