# Mergington High School Activities API

A FastAPI application for viewing extracurricular activities. Teachers sign in to add or remove student registrations; students can view activities and rosters without signing in.

## Features

- View all available extracurricular activities
- Teacher-only student registration and unregistration
- Teacher login with salted password hashes and signed sessions

## Getting Started

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Create a teacher account. The password is entered interactively and stored as a salted PBKDF2 hash in `src/teachers.json`:

   ```
   python -m src.create_teacher
   ```

3. Run the application:

   ```
   python -m uvicorn src.app:app --reload
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

`src/teachers.json` is local configuration and is intentionally ignored by Git. Set a persistent, high-entropy `SESSION_SECRET` in deployed environments so signed sessions remain valid across restarts and workers. When serving over HTTPS, also set `HTTPS_ONLY=true` to mark the session cookie secure.

## Tests

Install the test client dependency and run the focused API tests:

```
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| GET    | `/auth/session`                                                    | Get the current login status                                        |
| POST   | `/auth/login`                                                      | Sign in as a teacher                                                |
| POST   | `/auth/logout`                                                     | Sign out                                                            |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Register a student (teacher login required)                         |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher login required)                    |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity data is stored in memory, which means registrations reset when the server restarts.
