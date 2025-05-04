from pydantic import BaseModel, Field, NonNegativeFloat
from typing import Optional, Any
from typing import Dict
class WalletInitRequest(BaseModel):
    private_key: Optional[str] = None

class WalletInfoResponse(BaseModel):
    address: str
    balance: NonNegativeFloat
    publicKey: str
    privateKey: str

class TransactRequest(BaseModel):
    recipient: str
    amount: float = Field(gt=0)
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")

class TransactResponse(BaseModel):
    message: str
    transaction: Any  # Using Any to avoid recursive type issues
    fee: NonNegativeFloat
    size: int
    timestamp: float
    balance_info: dict

class FeeRateResponse(BaseModel):
    fee_rate: float
    priority_multipliers: Dict[str, float]
    mempool_size: int
    block_fullness: float