from fastapi import APIRouter, Depends, HTTPException, Query
from dependencies import get_blockchain, get_transaction_pool, get_pubsub, get_wallet
from models.transaction import Transaction
from schemas.blockchain import (
    BlockchainSchema, BlockchainRangeResponse, BlockchainHeightResponse,
    HalvingResponse, MineBlockRequest, MineBlockResponse, BlockSchema,
    PaginatedBlocksResponse
)
from typing import Optional, List
import logging
from models.blockchain import Blockchain
from models.transaction_pool import TransactionPool
from services.pubsub import PubSub
from models.wallet import Wallet
from math import ceil


logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

@router.get("/blockchain", response_model=BlockchainSchema, status_code=200)
async def route_blockchain(blockchain: Blockchain = Depends(get_blockchain)):
    try:
        return blockchain.to_json()
    except Exception as e:
        logger.error(f"Error fetching blockchain: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

#lastest    block
@router.get("/blockchain/paginated", response_model=PaginatedBlocksResponse, status_code=200)
async def get_paginated_blocks(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    blockchain: Blockchain = Depends(get_blockchain)
):
    """
    Get paginated blocks from latest to oldest
    """
    try:
        if not blockchain.chain:
            raise HTTPException(status_code=404, detail="No blocks found")
            
        total_blocks = len(blockchain.chain)
        total_pages = ceil(total_blocks / page_size)
        
        if page > total_pages:
            raise HTTPException(status_code=400, detail="Page number exceeds total pages")
        
        # Calculate start and end indices (reversed to get latest first)
        start = max(0, total_blocks - page * page_size)
        end = total_blocks - (page - 1) * page_size
        
        # Ensure we don't go below 0
        start = max(0, start)
        end = max(0, end)
        
        blocks = blockchain.chain[start:end]
        # Reverse to maintain chronological order within the page
        blocks = blocks[::-1]
        
        return {
            "blocks": [block.to_json() for block in blocks],
            "page": page,
            "page_size": page_size,
            "total_blocks": total_blocks,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching paginated blocks: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/blockchain/latest", response_model=List[BlockSchema], status_code=200)
async def get_latest_blocks(
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    blockchain: Blockchain = Depends(get_blockchain)
):
    """
    Get latest N blocks (alternative to pagination)
    """
    try:
        if not blockchain.chain:
            raise HTTPException(status_code=404, detail="No blocks found")
            
        blocks = blockchain.chain[-limit:]
        # Return in reverse order (latest first)
        return [block.to_json() for block in reversed(blocks)]
    except Exception as e:
        logger.error(f"Error fetching latest blocks: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Update the range endpoint to support reverse indexing
@router.get("/blockchain/range", response_model=BlockchainRangeResponse, status_code=200)
async def route_blockchain_range(
    start: int = Query(0, ge=0),
    end: int = Query(DEFAULT_PAGE_SIZE, ge=0),
    reverse: bool = Query(False, description="Return blocks in reverse order (latest first)"),
    blockchain: Blockchain = Depends(get_blockchain)
):
    try:
        total_blocks = len(blockchain.chain)
        
        if start >= total_blocks:
            return {"chain": []}
            
        # Handle negative indices (count from end)
        if start < 0:
            start = max(0, total_blocks + start)
        if end < 0:
            end = max(0, total_blocks + end)
            
        if start >= end:
            raise HTTPException(status_code=400, detail="Invalid range parameters")
            
        blocks = blockchain.chain[start:end]
        
        if reverse:
            blocks = blocks[::-1]
            
        return {"chain": [block.to_json() for block in blocks]}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid range parameters")
    except Exception as e:
        logger.error(f"Error fetching blockchain range: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/mine", response_model=MineBlockResponse, status_code=200)
async def route_mine(
    request: MineBlockRequest,
    blockchain: Blockchain = Depends(get_blockchain),
    transaction_pool: TransactionPool = Depends(get_transaction_pool),
    pubsub: PubSub = Depends(get_pubsub),
    wallet: Optional[Wallet] = Depends(get_wallet)
):
    try:
        if not wallet or not blockchain or not transaction_pool or not pubsub:
            raise HTTPException(status_code=400, detail="Blockchain, transaction pool, wallet, or PubSub not initialized")
        transactions = transaction_pool.get_priority_transactions()[:10]
        valid_transactions = []
        for tx in transactions:
            try:
                Transaction.is_valid(tx)
                valid_transactions.append(tx)
            except Exception as e:
                logger.warning(f"Invalid transaction {tx.id} skipped: {str(e)}")
        total_fees = sum(tx.fee for tx in valid_transactions)
        miner_address = request.miner_address or wallet.address
        coinbase_tx = Transaction.create_coinbase(miner_address, blockchain.current_height + 1, total_fees)
        all_transactions = [coinbase_tx] + valid_transactions
        new_block = blockchain.add_block(all_transactions)
        pubsub.save_block_to_db(new_block)
        transaction_pool.clear_blockchain_transactions(blockchain)
        pubsub.broadcast_block_sync(new_block)
        confirmed_balance = wallet.calculate_balance(blockchain, wallet.address) if wallet else 0.0
        return {
            "message": "Block mined successfully",
            "block": new_block.to_json(),
            "reward": coinbase_tx.output[miner_address],
            "confirmed_balance": confirmed_balance
        }
    except Exception as e:
        logger.error(f"Unexpected error in mining: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/blockchain/height", response_model=BlockchainHeightResponse, status_code=200)
async def route_blockchain_height(blockchain: Blockchain = Depends(get_blockchain)):
    try:
        return {"height": blockchain.current_height}
    except Exception as e:
        logger.error(f"Error fetching blockchain height: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/blockchain/halving", response_model=HalvingResponse, status_code=200)
async def route_blockchain_halving(blockchain: Blockchain = Depends(get_blockchain)):
    try:
        from models.transaction import HALVING_INTERVAL, BLOCK_SUBSIDY
        current_height = blockchain.current_height
        halvings = current_height // HALVING_INTERVAL
        subsidy = BLOCK_SUBSIDY // (2 ** halvings)
        return {"halvings": halvings, "subsidy": subsidy}
    except Exception as e:
        logger.error(f"Error fetching halving information: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/blockchain/height/{height}", response_model=BlockSchema, status_code=200)
async def route_blockchain_height_by_height(height: int, blockchain: Blockchain = Depends(get_blockchain)):
    try:
        if height < 0 or height > blockchain.current_height:
            raise HTTPException(status_code=400, detail="Invalid block height")
        block = None
        for b in blockchain.chain:
            if b.height == height:
                block = b
                break
        if not block:
            raise HTTPException(status_code=404, detail="Block not found")
        return block.to_json()
    except Exception as e:
        logger.error(f"Error fetching block by height: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/blockchain/hash/{block_hash}", response_model=BlockSchema, status_code=200)
async def route_blockchain_hash(block_hash: str, blockchain: Blockchain = Depends(get_blockchain)):
    try:
        block = None
        for b in blockchain.chain:
            if b.hash == block_hash:
                block = b
                break
        if not block:
            raise HTTPException(status_code=404, detail="Block not found")
        return block.to_json()
    except Exception as e:
        logger.error(f"Error fetching block by hash: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/blockchain/tx/{tx_id}", response_model=BlockSchema, status_code=200)
async def route_blockchain_tx(tx_id: str, blockchain: Blockchain = Depends(get_blockchain)):
    try:
        block = None
        for b in blockchain.chain:
            for tx in b.data:
                if tx["id"] == tx_id:
                    block = b
                    break
            if block:
                break
        if not block:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return block.to_json()
    except Exception as e:
        logger.error(f"Error fetching block by transaction ID: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")