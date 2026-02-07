from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict

class TransactionType(str, Enum):
    RESET = "RESET"
    BET_WIN = "BET_WIN"
    BET_LOSS = "BET_LOSS"
    ADJUSTMENT = "ADJUSTMENT"

class BankrollState(BaseModel):
    """Snapshot of the current bankroll integrity."""
    id: int
    current_units: float
    initial_units: float
    peak_units: float
    max_drawdown: float
    kelly_fraction: float
    status: str
    last_updated: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Transaction(BaseModel):
    """Record of a financial movement."""
    id: int
    timestamp: datetime
    type: TransactionType
    amount: float
    balance_after: float
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
