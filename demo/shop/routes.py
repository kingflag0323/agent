"""Intentionally vulnerable source fixture. Never served or executed by Sentinel."""
from fastapi import APIRouter
from services import get_user, run_diagnostic

router = APIRouter()

@router.get("/api/user")
def user_controller(id: str):
    return get_user(id)

@router.get("/api/diagnostic")
def diagnostic_controller(host: str):
    return run_diagnostic(host)

@router.get("/api/health")
def health_controller():
    return {"status": "ok"}
