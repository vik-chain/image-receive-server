from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, confloat
from sqlmodel import SQLModel, Field as SQLField, Session, create_engine, select
import os

# ---------- Config ----------
API_KEY = os.getenv("API_KEY", "dev-key")  # set on Render; keep as-is locally
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local.db")

# ---------- DB Models ----------
class Run(SQLModel, table=True):
    pk: Optional[int] = SQLField(default=None, primary_key=True)
    id: str = SQLField(index=True, unique=True)      # your external id/timestamp
    items_processed: int = SQLField(default=0)

class Composition(SQLModel, table=True):
    pk: Optional[int] = SQLField(default=None, primary_key=True)
    run_fk: int = SQLField(foreign_key="run.pk", index=True)
    material: str
    percentage: float

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# ---------- Schemas ----------
class CompositionIn(BaseModel):
    material: str = Field(min_length=1)
    percentage: confloat(ge=0, le=100)

class RunIn(BaseModel):
    id: str = Field(min_length=1)
    items_processed: int = Field(ge=0)
    composition: List[CompositionIn]

class RunOut(RunIn):
    pass

class RunMeta(BaseModel):
    id: str
    items_processed: int


# ---------- Auth ----------
def require_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")

# ---------- App ----------
app = FastAPI(title="Ultra-Minimal Composition API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock this down later to your dashboard origin(s)
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/v1/runs", dependencies=[Depends(require_api_key)], response_model=RunOut)
def upsert_run(payload: RunIn, session: Session = Depends(get_session)):
    # upsert by id (idempotent)
    run = session.exec(select(Run).where(Run.id == payload.id)).first()
    if run is None:
        run = Run(id=payload.id, items_processed=payload.items_processed)
        session.add(run)
        session.commit()
        session.refresh(run)
    else:
        run.items_processed = payload.items_processed
        session.add(run)
        session.commit()

        # wipe old composition rows
        session.query(Composition).filter(Composition.run_fk == run.pk).delete()
        session.commit()

    # insert fresh composition rows
    for c in payload.composition:
        session.add(Composition(run_fk=run.pk, material=c.material, percentage=c.percentage))
    session.commit()

    return payload

@app.get("/v1/runs/latest", response_model=RunOut)
def get_latest(session: Session = Depends(get_session)):
    # "latest" by highest pk (insert/update order)
    run = session.exec(select(Run).order_by(Run.pk.desc())).first()
    if not run:
        raise HTTPException(status_code=404, detail="no data yet")
    comps = session.exec(select(Composition).where(Composition.run_fk == run.pk)).all()
    return RunOut(
        id=run.id,
        items_processed=run.items_processed,
        composition=[{"material": c.material, "percentage": c.percentage} for c in comps],
    )

@app.get("/v1/runs/{run_id}", response_model=RunOut)
def get_by_id(run_id: str, session: Session = Depends(get_session)):
    run = session.exec(select(Run).where(Run.id == run_id)).first()
    if not run:
        raise HTTPException(status_code=404, detail="not found")
    comps = session.exec(select(Composition).where(Composition.run_fk == run.pk)).all()
    return RunOut(
        id=run.id,
        items_processed=run.items_processed,
        composition=[{"material": c.material, "percentage": c.percentage} for c in comps],
    )

@app.get("/v1/runs", response_model=List[RunMeta])
def list_runs(session: Session = Depends(get_session), limit: int = 50):
    # newest first by pk
    runs = session.exec(select(Run).order_by(Run.pk.desc()).limit(limit)).all()
    return [RunMeta(id=r.id, items_processed=r.items_processed) for r in runs]