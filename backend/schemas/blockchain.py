from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt
from typing import List, Dict, Any, Optional
from .transaction import TransactionSchema
class BlockSchema(BaseModel):
    timestamp: float
    last_hash: str
    hash: str
    data: List[TransactionSchema]
    difficulty: PositiveInt
    nonce: NonNegativeInt
    height: NonNegativeInt
    version: PositiveInt
    merkle_root: str
    tx_count: NonNegativeInt

    class Config:
        from_attributes = True

class BlockchainSchema(BaseModel):
    chain: List[BlockSchema]
    utxo_set: Dict[str, Dict[str, float]]
    current_height: NonNegativeInt

class BlockchainRangeResponse(BaseModel):
    chain: List[BlockSchema]

class BlockchainHeightResponse(BaseModel):
    height: NonNegativeInt

class HalvingResponse(BaseModel):
    halvings: NonNegativeInt
    subsidy: float

class MineBlockRequest(BaseModel):
    miner_address: Optional[str] = None

class MineBlockResponse(BaseModel):
    message: str
    block: BlockSchema
    reward: float
    confirmed_balance: float



class PaginatedBlocksResponse(BaseModel):
    blocks: List[BlockSchema]
    page: int
    page_size: int
    total_blocks: int
    total_pages: int
    has_next: bool
    has_previous: bool