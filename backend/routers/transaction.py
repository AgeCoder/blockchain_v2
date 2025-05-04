from fastapi import APIRouter, Depends, HTTPException
from dependencies import get_blockchain, get_transaction_pool
from schemas.transaction import TransactionPoolSchema, TransactionByAddressSchema
from typing import List
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class TransactionResponseSchema:
    id: str
    input: dict
    output: dict
    fee: float
    size: int
    is_coinbase: bool
    status: str
    block_height: int = None
    timestamp: float

@router.get("/transaction", response_model=TransactionPoolSchema, status_code=200)
async def route_transaction_pool(transaction_pool=Depends(get_transaction_pool)):
    return transaction_pool.to_json()

@router.get("/transactions/{address}", response_model=List[TransactionByAddressSchema], status_code=200)
async def route_transactions_by_address(
    address: str,
    blockchain=Depends(get_blockchain),
    transaction_pool=Depends(get_transaction_pool)
):
    transactions = []
    # Check transaction pool (pending transactions)
    for tx in transaction_pool.transaction_data():
        if tx["input"].get("address") == address or address in tx["output"]:
            tx_data = {
                "id": tx["id"],
                "input": tx["input"],
                "output": tx["output"],
                "status": "pending",
                "timestamp": tx["input"].get("timestamp", time.time() * 1000000),
                "fee": tx.get("fee", 0),
            }
            transactions.append(tx_data)
    # Check blockchain (confirmed transactions)
    for block in blockchain.chain:
        for tx in block.data:
            if tx["input"].get("address") == address or address in tx["output"]:
                tx_data = {
                    "id": tx["id"],
                    "input": tx["input"],
                    "output": tx["output"],
                    "status": "confirmed",
                    "blockHeight": block.height,
                    "timestamp": tx["input"].get("timestamp", block.timestamp),
                    "fee": tx.get("fee", 0),
                }
                transactions.append(tx_data)
    # Sort by timestamp (newest first)
    transactions.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return transactions
#tracation by id
@router.get("/transaction/id/{transaction_id}", status_code=200)
async def route_transaction_by_id(
    transaction_id: str,
    blockchain=Depends(get_blockchain),
    transaction_pool=Depends(get_transaction_pool)
):
    """
    Get transaction by ID from either mempool or blockchain
    Returns:
        - Transaction details with status (pending/confirmed)
        - 404 if transaction not found
        - 500 for server errors
    """
    try:
        # Check transaction pool first (pending transactions)
        for tx in transaction_pool.transaction_data():
            if tx["id"] == transaction_id:
                return {
                    "id": tx["id"],
                    "input": tx["input"],
                    "output": tx["output"],
                    "fee": tx.get("fee", 0),
                    "size": tx.get("size", 0),
                    "is_coinbase": False,
                    "status": "pending",
                    "timestamp": tx["input"].get("timestamp", time.time() * 1000000)
                }

        # Check blockchain (confirmed transactions)
        for block in blockchain.chain:
            for tx in block.data:
                # Handle both dict and Transaction object cases
                tx_id = tx["id"] if isinstance(tx, dict) else tx.id
                if tx_id == transaction_id:
                    return {
                        "id": tx_id,
                        "input": tx["input"] if isinstance(tx, dict) else tx.input,
                        "output": tx["output"] if isinstance(tx, dict) else tx.output,
                        "fee": tx.get("fee", 0) if isinstance(tx, dict) else tx.fee,
                        "size": tx.get("size", 0) if isinstance(tx, dict) else tx.size,
                        "is_coinbase": tx.get("is_coinbase", False) if isinstance(tx, dict) else tx.is_coinbase,
                        "status": "confirmed",
                        "block_height": block.height,
                        "timestamp": tx["input"].get("timestamp", block.timestamp) if isinstance(tx, dict) else tx.input.timestamp
                    }

        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} not found in mempool or blockchain"
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error fetching transaction {transaction_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error while processing transaction"
        )