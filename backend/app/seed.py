"""초기 시드 데이터 (대공정 목록). `python -m app.seed` 로 직접 실행 가능."""
from .database import Base, SessionLocal, engine
from .models import MAJOR_PROCESS_SEED, MajorProcess


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = {mp.code for mp in db.query(MajorProcess).all()}
        for code, name in MAJOR_PROCESS_SEED:
            if code not in existing:
                db.add(MajorProcess(code=code, name=name))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seed complete.")
