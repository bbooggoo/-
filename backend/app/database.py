"""
DB 연결 설정.

기본값은 파일 기반 SQLite (로컬 실행/데모 용이성 목적).
운영 환경에서는 환경변수 DATABASE_URL 로 PostgreSQL 등을 지정해서 그대로 교체 가능
(SQLAlchemy 사용이므로 모델/쿼리 코드 변경 불필요).
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./spec_qa.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
