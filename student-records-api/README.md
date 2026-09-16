# Student Academic Records Management API

> **Production-ready** FastAPI + PostgreSQL REST API for managing university student records, course enrolments, grade computation, and GPA/CGPA analytics.

---

## 📁 Project Structure

```
student-records-api/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app, lifespan, middleware, routers
│   ├── database.py        # Engine (pooled), SessionLocal, DeclarativeBase
│   ├── models.py          # SQLAlchemy 2.0 ORM models + grade helpers
│   ├── schemas.py         # Pydantic v2 request / response schemas
│   ├── crud.py            # All DB queries & business logic (GPA, CGPA)
│   ├── dependencies.py    # get_db() dependency injection
│   └── routers/
│       ├── __init__.py
│       ├── students.py    # /students  CRUD + /students/{id}/transcript
│       ├── courses.py     # /courses   CRUD
│       └── records.py     # /records   CRUD
├── alembic/
│   ├── env.py             # Reads DATABASE_URL; passes metadata for autogenerate
│   ├── script.py.mako     # Migration file template
│   └── versions/          # Auto-generated migration scripts
├── alembic.ini
├── docker-compose.yml
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.11+
- Docker & Docker Compose (for the managed PostgreSQL instance)

### 2. Clone / unzip & enter the project

```bash
cd student-records-api
```

### 3. Create a virtual environment & install dependencies

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env if you need custom DB credentials
```

### 5. Start PostgreSQL via Docker

```bash
docker compose up -d
# Wait for the health-check to pass (~10 s)
docker compose ps
```

### 6. Run database migrations

```bash
alembic upgrade head
```

### 7. Start the development server

```bash
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## 🗄️ Database Schema

### `students`
| Column           | Type         | Constraints                    |
|------------------|--------------|--------------------------------|
| id               | UUID         | PK, default uuid4              |
| matric_number    | VARCHAR(50)  | NOT NULL, UNIQUE, INDEX        |
| first_name       | VARCHAR(100) | NOT NULL                       |
| last_name        | VARCHAR(100) | NOT NULL                       |
| email            | VARCHAR(255) | NOT NULL, UNIQUE, INDEX        |
| department       | VARCHAR(150) | nullable                       |
| enrollment_year  | INTEGER      | nullable                       |
| created_at       | TIMESTAMPTZ  | server_default NOW()           |
| updated_at       | TIMESTAMPTZ  | server_default NOW(), onupdate |

### `courses`
| Column       | Type         | Constraints                      |
|--------------|--------------|----------------------------------|
| id           | INTEGER      | PK, autoincrement                |
| course_code  | VARCHAR(20)  | NOT NULL, UNIQUE, INDEX          |
| title        | VARCHAR(255) | NOT NULL                         |
| credit_units | INTEGER      | NOT NULL, CHECK(credit_units > 0)|

### `academic_records`
| Column      | Type        | Constraints                                        |
|-------------|-------------|----------------------------------------------------|
| id          | INTEGER     | PK, autoincrement                                  |
| student_id  | UUID        | FK → students.id ON DELETE CASCADE                 |
| course_id   | INTEGER     | FK → courses.id ON DELETE RESTRICT                 |
| semester    | VARCHAR(50) | NOT NULL                                           |
| score       | FLOAT       | NOT NULL, CHECK(0 ≤ score ≤ 100)                   |
| grade       | ENUM        | A/B/C/D/E/F — server-computed                      |
| grade_point | FLOAT       | server-computed                                    |
| —           | —           | UNIQUE(student_id, course_id, semester)             |
| —           | —           | INDEX(student_id, semester)                        |

---

## 🎓 Grade Scale (5-point)

| Score Range | Grade | Grade Point |
|-------------|-------|-------------|
| 70 – 100    | A     | 5.0         |
| 60 – 69     | B     | 4.0         |
| 50 – 59     | C     | 3.0         |
| 45 – 49     | D     | 2.0         |
| 40 – 44     | E     | 1.0         |
| 0  – 39     | F     | 0.0         |

---

## 📡 API Endpoints

### Students
| Method | Path                           | Description                        | Status |
|--------|--------------------------------|------------------------------------|--------|
| POST   | `/students/`                   | Create a student                   | 201    |
| GET    | `/students/`                   | List students (paginated, filtered)| 200    |
| GET    | `/students/{id}`               | Get student by UUID                | 200    |
| PUT    | `/students/{id}`               | Update student info                | 200    |
| DELETE | `/students/{id}`               | Delete student (cascades records)  | 204    |
| GET    | `/students/{id}/transcript`    | Full transcript with GPA/CGPA      | 200    |

### Courses
| Method | Path             | Description             | Status |
|--------|------------------|-------------------------|--------|
| POST   | `/courses/`      | Create a course         | 201    |
| GET    | `/courses/`      | List courses (paginated)| 200    |
| GET    | `/courses/{id}`  | Get course by ID        | 200    |
| PUT    | `/courses/{id}`  | Update course           | 200    |
| DELETE | `/courses/{id}`  | Delete course           | 204    |

### Academic Records
| Method | Path             | Description                     | Status |
|--------|------------------|---------------------------------|--------|
| POST   | `/records/`      | Create a record (grade computed)| 201    |
| GET    | `/records/{id}`  | Get record by ID                | 200    |
| PUT    | `/records/{id}`  | Update score/semester           | 200    |
| DELETE | `/records/{id}`  | Delete record                   | 204    |

### List Students — Query Parameters
| Param          | Type   | Description                                   |
|----------------|--------|-----------------------------------------------|
| `limit`        | int    | Page size (1–200, default 20)                 |
| `offset`       | int    | Skip N records (default 0)                    |
| `search`       | string | Partial match: first_name, last_name, email   |
| `department`   | string | Partial department filter                     |
| `matric_number`| string | Exact matric_number lookup                    |

---

## 🔄 Sample Workflow (cURL)

```bash
# 1. Create a student
curl -s -X POST http://localhost:8000/students/ \
  -H "Content-Type: application/json" \
  -d '{
    "matric_number": "CSC/2020/001",
    "first_name": "Amara",
    "last_name": "Okafor",
    "email": "amara.okafor@university.edu",
    "department": "Computer Science",
    "enrollment_year": 2020
  }' | python -m json.tool

# 2. Create a course
curl -s -X POST http://localhost:8000/courses/ \
  -H "Content-Type: application/json" \
  -d '{"course_code": "CS301", "title": "Data Structures", "credit_units": 3}' \
  | python -m json.tool

# 3. Enrol the student (replace UUIDs from the responses above)
curl -s -X POST http://localhost:8000/records/ \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "<STUDENT_UUID>",
    "course_id": 1,
    "semester": "First Semester 2023/2024",
    "score": 75.0
  }' | python -m json.tool
# → grade: "A", grade_point: 5.0

# 4. Get transcript
curl -s http://localhost:8000/students/<STUDENT_UUID>/transcript | python -m json.tool
```

---

## 🛠️ Alembic Migration Commands

```bash
# Create a new autogenerated migration
alembic revision --autogenerate -m "your description here"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

---

## 🐳 Docker Compose Reference

```bash
docker compose up -d          # Start PostgreSQL in background
docker compose ps             # Check health status
docker compose logs -f db     # Tail database logs
docker compose down           # Stop containers (data persisted in volume)
docker compose down -v        # Stop + wipe the data volume
```

---

## 🏭 Production Checklist

- [ ] Set `echo=False` in `database.py` (already set)
- [ ] Restrict `allow_origins` in CORS middleware to your frontend domain
- [ ] Use `DATABASE_URL` with SSL: `?sslmode=require`
- [ ] Run behind Nginx / a reverse proxy
- [ ] Use Gunicorn + UvicornWorker: `gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4`
- [ ] Set up structured JSON logging for production observability
- [ ] Add rate-limiting middleware (e.g., `slowapi`)
- [ ] Implement authentication (JWT / OAuth2)
