from fastapi import FastAPI,Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.session import engine
from db.models import Base
from db.session import SessionLocal
from db.seed import seed_data

Base.metadata.create_all(bind=engine)

app = FastAPI(title="wattwise backend")

@app.get("/")
def health_check():
    return {"status":"wattwise backend is running"}

@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"db": "connected"}

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    seed_data(db)
    db.close()