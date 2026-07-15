"""FastAPI thin server (§1.1). All numbers come from the pure core; this layer only routes."""

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from . import config
from .api.routes import router

app = FastAPI(title="배터리 기상 예보 API", version="0.1.0-M0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in config.CORS_ORIGINS if o],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    # Common error shape (§6): {"error": {"code", "message"}}
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.status_code, "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": 422, "message": str(exc.errors())}},
    )
