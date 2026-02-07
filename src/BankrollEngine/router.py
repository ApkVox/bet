from fastapi import APIRouter, HTTPException, Depends
from typing import Literal
from pydantic import BaseModel

from .service import BankrollService, get_bankroll_service
from .models import BankrollState

router = APIRouter(prefix="/bankroll", tags=["Bankroll"])

def get_service():
    return get_bankroll_service()

class UpdateBankrollRequest(BaseModel):
    result: Literal["WIN", "LOSS", "PUSH"]
    stake_units: float
    profit_units: float = 0.0
    note: str | None = None

@router.get("/state", response_model=BankrollState)
def get_bankroll_state(service: BankrollService = Depends(get_service)):
    return service.get_state()

@router.get("/system-state")
def get_system_state(service: BankrollService = Depends(get_service)):
    """
    Observability endpoint for monitoring system health.
    Read-only.
    """
    return service.get_observability_metrics()

@router.get("/risk-metrics")
def get_risk_metrics(service: BankrollService = Depends(get_service)):
    """
    Subset of metrics focused on Risk.
    """
    metrics = service.get_observability_metrics()
    return {
        "drawdown": metrics["drawdown"],
        "kelly_fraction": metrics["kelly_fraction"],
        "blocked_bets": metrics["blocked_bets"],
        "avg_ev": metrics["avg_ev"]
    }

@router.get("/status")
def get_status(service: BankrollService = Depends(get_service)):
    """
    Simple status check (ACTIVE / DEGRADED / PAUSED).
    """
    return {"status": service.operational_status}

# Legacy / Admin endpoints
@router.post("/update")
def update_bankroll(update: UpdateBankrollRequest, service: BankrollService = Depends(get_service)):
    # Note: This updates the REAL bankroll. Should be protected or internal only.
    try:
        new_balance = service.update_bankroll(
            result=update.result,
            stake_units=update.stake_units,
            profit_units=update.profit_units,
            note=update.note
        )
        return {"status": "success", "new_balance": new_balance}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Removed reset for safety in production unless explicitly requested, 
# but keeping strictly update/state/observability.
