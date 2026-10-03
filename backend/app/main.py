from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import Employee
from .routers import campaigns, policies, reports
from .seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(
    title="Policy Management & Attestation Platform",
    description=(
        "Publish policies, have people attest to them, and prove afterwards exactly which "
        "words each person agreed to and when."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(policies.router)
app.include_router(campaigns.router)
app.include_router(reports.router)


@app.get("/api/employees")
def list_employees(db: Session = Depends(get_db)):
    """Stands in for an identity provider — there is no auth in this project."""
    people = db.execute(select(Employee).order_by(Employee.name)).scalars().all()
    return [
        {"id": p.id, "name": p.name, "email": p.email, "department": p.department}
        for p in people
    ]


@app.get("/api/health")
def health():
    return {"status": "ok"}
