from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import corrections, major_processes, owners, qa, spec_sheets, validation
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed()
    yield


app = FastAPI(title="반도체 제원 질의응답 플랫폼 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 데모 목적. 운영 배포 시 프론트엔드 도메인으로 제한 필요.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(major_processes.router)
app.include_router(owners.router)
app.include_router(spec_sheets.router)
app.include_router(validation.router)
app.include_router(qa.router)
app.include_router(corrections.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
