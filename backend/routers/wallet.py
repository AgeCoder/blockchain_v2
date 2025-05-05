from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Optional, Annotated, Dict
import logging
from models.wallet import Wallet
from models.transaction import Transaction
from models.blockchain import Blockchain
from models.transaction_pool import TransactionPool
from services.pubsub import PubSub
from services.fee_rate_estimator import FeeRateEstimator
from schemas.wallet import WalletInitRequest, WalletInfoResponse, TransactRequest, TransactResponse, FeeRateResponse,WalletInfoResponseinit_wallet
from core.config import BASE_TX_SIZE, MIN_FEE, DEFAULT_FEE_RATE, BLOCK_SIZE_LIMIT, PRIORITY_MULTIPLIERS
from dependencies import get_blockchain, get_transaction_pool, get_pubsub, app, get_fee_rate_estimator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Create type aliases for dependency injection
BlockchainDep = Annotated[Blockchain, Depends(get_blockchain)]
TransactionPoolDep = Annotated[TransactionPool, Depends(get_transaction_pool)]
PubSubDep = Annotated[PubSub, Depends(get_pubsub)]
WalletDep = Annotated[Optional[Wallet], Depends()]

async def get_wallet(authorization: str = Header(None)) -> Wallet:
    try:
        if authorization and authorization.startswith("Bearer "):
            private_key_hex = authorization.replace("Bearer ", "")
            wallet = Wallet.from_private_key_hex(private_key_hex)
            wallet.blockchain = get_blockchain()
            return wallet
        # Fallback to app.state.wallet
        wallet = app.state.wallet
        if not wallet:
            raise HTTPException(status_code=400, detail="No wallet initialized")
        return wallet
    except Exception as e:
        logger.error(f"Failed to initialize wallet: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid private key or no wallet initialized")

@router.post("/wallet", response_model=WalletInfoResponseinit_wallet, status_code=200)
@router.options("/wallet", include_in_schema=False)
async def init_wallet(
    request: WalletInitRequest,
    blockchain: Blockchain = Depends(get_blockchain),
):
    try:
        private_key_hex = request.private_key or None
        if private_key_hex:
            private_key_hex = private_key_hex.strip()
            if not (len(private_key_hex) == 64 and all(c in '0123456789abcdefABCDEF' for c in private_key_hex)):
                raise HTTPException(status_code=400, detail="Invalid private key format: must be 64-character hexadecimal")
            try:
                wallet = Wallet.from_private_key_hex(private_key_hex)
                wallet.blockchain = blockchain
            except ValueError as e:
                logger.error(f"Invalid private key: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Invalid private key: {str(e)}")
        else:
            wallet = Wallet(blockchain=blockchain)
        
        app.state.wallet = wallet
        
        return {
            "address": wallet.address,
            "balance": wallet.balance,
            "publicKey": wallet.public_key,
            "privateKey": wallet.get_private_key_hex(),
        }
    except Exception as e:
        logger.error(f"Error initializing wallet: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize wallet: {str(e)}")

@router.get("/wallet/info", response_model=WalletInfoResponse, status_code=200)
async def route_wallet_info(
    wallet: Wallet = Depends(get_wallet),
    transaction_pool: TransactionPool = Depends(get_transaction_pool),
    ):
    if not wallet:
        raise HTTPException(status_code=400, detail="Wallet not initialized")
    return {
        "address": wallet.address,
        "balance": wallet.balance,
        "publicKey": wallet.public_key,
        "pending_spends": Wallet.pending_spends(transaction_pool.transaction_map , wallet.address),
    }

@router.post("/wallet/transact", response_model=TransactResponse, status_code=200)
async def route_wallet_transact(
    request: TransactRequest,
    wallet: Wallet = Depends(get_wallet),
    blockchain: Blockchain = Depends(get_blockchain),
    transaction_pool: TransactionPool = Depends(get_transaction_pool),
    pubsub: PubSub = Depends(get_pubsub),
    fee_rate_estimator: FeeRateEstimator = Depends(get_fee_rate_estimator),
):
    try:
        if not wallet:
            raise HTTPException(status_code=400, detail="Wallet not initialized")
        if not blockchain or not transaction_pool or not pubsub:
            raise HTTPException(status_code=400, detail="Blockchain, transaction pool, or PubSub not initialized")
        if request.recipient == wallet.address:
            raise HTTPException(status_code=400, detail="Cannot send to self")
        logger.info(f"Transact request: {request}")
        # Get dynamic fee rate based on priority
        base_fee_rate = fee_rate_estimator.get_fee_rate()
        priority_multiplier = PRIORITY_MULTIPLIERS.get(request.priority, 1.0)
        fee_rate = base_fee_rate * priority_multiplier
        
        confirmed_balance = wallet.calculate_balance(blockchain, wallet.address)
        pending_txs = [
            tx for tx in transaction_pool.transaction_map.values()
            if tx.input.get("address") == wallet.address
        ]
        total_pending_spend = sum(
            sum(v for k, v in tx.output.items() if k != wallet.address) + tx.fee
            for tx in pending_txs
        )
        available_balance = confirmed_balance - total_pending_spend
        
        if available_balance < 0:
            error_msg = (
                f"Insufficient funds. Available: {available_balance:.4f} COIN, "
                f"Pending transactions: {len(pending_txs)}"
            )
            raise HTTPException(status_code=400, detail=error_msg)

        if request.amount > available_balance:
            error_msg = (
                f"Insufficient funds. Available: {available_balance:.4f} COIN, "
                f"Requested: {request.amount:.4f} COIN (Pending transactions: {len(pending_txs)})"
            )
            raise HTTPException(status_code=400, detail=error_msg)
        if request.amount + MIN_FEE > available_balance:
            error_msg = (
                f"Transaction too small. Minimum transaction size is {MIN_FEE:.4f} COIN "
                f"for the requested amount of {request.amount:.4f} COIN."
            )
            raise HTTPException(status_code=400, detail=error_msg)
        if request.amount + MIN_FEE > confirmed_balance:
            error_msg = (
                f"Transaction too small. Minimum transaction size is {MIN_FEE:.4f} COIN "
                f"for the requested amount of {request.amount:.4f} COIN."
            )
            raise HTTPException(status_code=400, detail=error_msg)

        # Create transaction to estimate size and fee
        try:
            existing_tx = transaction_pool.existing_transaction(wallet.address)
            if existing_tx:
                existing_tx.update(wallet, request.recipient, request.amount, fee_rate=fee_rate)
                Transaction.is_valid(existing_tx)
                transaction_pool.set_transaction(existing_tx)
                transaction = existing_tx
            else:
                transaction = Transaction(
                    sender_wallet=wallet,
                    recipient=request.recipient,
                    amount=request.amount,
                    fee_rate=fee_rate
                )
                Transaction.is_valid(transaction)
                transaction_pool.set_transaction(transaction)
        except Exception as e:
            logger.error(f"Transaction creation/validation failed: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        total_cost = request.amount + transaction.fee
        if total_cost > available_balance:
            error_msg = (
                f"Insufficient funds. Available: {available_balance:.4f} COIN, "
                f"Required: {total_cost:.4f} COIN (Amount: {request.amount:.4f} + Fee: {transaction.fee:.4f}). "
                f"Pending transactions: {len(pending_txs)}"
            )
            raise HTTPException(status_code=400, detail=error_msg)
                
        try:
            pubsub.broadcast_transaction_sync(transaction)
        except Exception as e:
            logger.error(f"Broadcast failed: {str(e)}")
            transaction_pool.transaction_map.pop(transaction.id, None)
            raise HTTPException(status_code=500, detail=f"Broadcast failed: {str(e)}")
        
        return {
            "message": "Transaction created successfully",
            "transaction": transaction.to_json(),
            "fee": transaction.fee,
            "size": transaction.size,
            "timestamp": transaction.input["timestamp"],
            "balance_info": {
                "confirmed_balance": confirmed_balance,
                "pending_spend": total_pending_spend + total_cost,
                "available_balance": available_balance - total_cost,
            },
        }
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid numeric value: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/fee-rate", response_model=FeeRateResponse, status_code=200)
async def route_fee_rate(
    fee_rate_estimator: FeeRateEstimator = Depends(get_fee_rate_estimator),
    blockchain: Blockchain = Depends(get_blockchain)
):
    try:
        fee_rate = fee_rate_estimator.get_fee_rate()
        mempool_size = len(fee_rate_estimator.transaction_pool.transaction_map)
        # Calculate average block fullness for last 10 blocks
        recent_blocks = blockchain.chain[-10:] if len(blockchain.chain) >= 10 else blockchain.chain
        block_fullness = (
            sum(sum(len(str(tx)) for tx in block.data) for block in recent_blocks) / 
            (len(recent_blocks) * BLOCK_SIZE_LIMIT)
        ) if recent_blocks else 0.0
        return {
            "fee_rate": fee_rate,
            "priority_multipliers": PRIORITY_MULTIPLIERS,
            "mempool_size": mempool_size,
            "block_fullness": block_fullness
        }
    except Exception as e:
        logger.error(f"Error retrieving fee rate: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")