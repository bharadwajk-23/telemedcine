"""Read endpoints for patients and calls."""
from fastapi import APIRouter, HTTPException

from app import storage

router = APIRouter()


@router.get("/api/patients")
def list_patients():
    """Only one hardcoded patient in this starter."""
    return [storage.get_patient()]


@router.get("/api/patients/{patient_id}/calls")
def list_calls(patient_id: str):
    return storage.list_calls_for_patient(patient_id)


@router.get("/api/calls/{call_id}")
def get_call(call_id: str):
    call = storage.get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call
