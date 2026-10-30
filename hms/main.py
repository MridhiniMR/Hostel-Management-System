from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder

from hms.database import Base, engine, get_db
from hms.api import router as api_router
from hms.config import APP_NAME, REQUIRE_HTTPS
from hms.errors import DomainError
from hms import models  # noqa: F401 - ensure SQLAlchemy models are registered before create_all
from hms.web import router as web_router

@asynccontextmanager
async def lifespan(application: FastAPI):
    # For this mini-project's first implementation, create tables automatically.
    # A production deployment should move to versioned migrations.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=APP_NAME,
    version="0.1.0",
    description="Layered Hostel Management System API and browser interface.",
    lifespan=lifespan,
)


@app.middleware("http")
async def enforce_https_in_deployment(request: Request, call_next):
    # Enable only when TLS is provided by the application server or a correctly configured trusted proxy.
    if REQUIRE_HTTPS and request.url.scheme != "https":
        https_url = request.url.replace(scheme="https")
        return RedirectResponse(url=str(https_url), status_code=307)
    return await call_next(request)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.code, "message": exc.message, "details": exc.details},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    fields = []
    for error in exc.errors():
        fields.append({"field": ".".join(str(part) for part in error.get("loc", ()) if part != "body"), "message": error.get("msg", "Invalid value."), "type": error.get("type", "validation_error")})
    return JSONResponse(
        status_code=422,
        content={"error_code": "VALIDATION_ERROR", "message": "Request validation failed.", "details": {"fields": fields}},
    )


@app.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unavailable",
                "database": "unavailable",
            },
        )

    return {
        "status": "ok",
        "database": "ok",
    }

app.mount("/static", StaticFiles(directory="hms/static"), name="static")
app.include_router(api_router)
app.include_router(web_router)
