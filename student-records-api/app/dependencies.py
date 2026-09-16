"""
dependencies.py
──────────────────────────────────────────────────────────────────────────────
FastAPI dependency functions injected into route handlers.

`get_db` yields a SQLAlchemy Session that is automatically closed (and rolled
back on error) after each request, ensuring connections are always returned to
the pool.
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session for the duration of a single HTTP request.

    Usage in a route::

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
