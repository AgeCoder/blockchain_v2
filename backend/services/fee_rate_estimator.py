import asyncio
import logging
import time
from models.blockchain import Blockchain
from models.transaction_pool import TransactionPool
from core.config import (
    DEFAULT_FEE_RATE, MEMPOOL_THRESHOLD, BLOCK_FULLNESS_THRESHOLD,
    FEE_RATE_UPDATE_INTERVAL, BLOCK_SIZE_LIMIT
)

logger = logging.getLogger(__name__)

class FeeRateEstimator:
    def __init__(self, blockchain: Blockchain, transaction_pool: TransactionPool):
        self.blockchain = blockchain
        self.transaction_pool = transaction_pool
        self.current_fee_rate = DEFAULT_FEE_RATE
        self.last_update = 0
        self.lock = asyncio.Lock()

    async def update_fee_rate(self):
        """Update the fee rate based on mempool size and block fullness."""
        try:
            async with self.lock:
                mempool_size = len(self.transaction_pool.transaction_map)
                # Calculate average block fullness for last 10 blocks
                recent_blocks = self.blockchain.chain[-10:] if len(self.blockchain.chain) >= 10 else self.blockchain.chain
                block_fullness = (
                    sum(sum(len(str(tx)) for tx in block.data) for block in recent_blocks) / 
                    (len(recent_blocks) * BLOCK_SIZE_LIMIT)
                ) if recent_blocks else 0.0
                
                # Adjust fee rate
                fee_rate = DEFAULT_FEE_RATE
                if mempool_size > MEMPOOL_THRESHOLD:
                    fee_rate *= (1 + (mempool_size / MEMPOOL_THRESHOLD) * 0.5)
                if block_fullness > BLOCK_FULLNESS_THRESHOLD:
                    fee_rate *= (1 + (block_fullness / BLOCK_FULLNESS_THRESHOLD) * 0.3)
                
                self.current_fee_rate = max(fee_rate, DEFAULT_FEE_RATE)
                self.last_update = time.time()
                logger.info(f"Updated fee rate: {self.current_fee_rate:.8f} COIN/byte, "
                           f"mempool_size: {mempool_size}, block_fullness: {block_fullness:.2f}")
        except Exception as e:
            logger.error(f"Error updating fee rate: {str(e)}")

    async def ensure_updated(self):
        """Ensure the fee rate is updated if stale."""
        if time.time() - self.last_update > FEE_RATE_UPDATE_INTERVAL:
            await self.update_fee_rate()

    def get_fee_rate(self):
        """Get the current fee rate, updating if necessary."""
        try:
            # Use ensure_updated directly since FastAPI handles the event loop
            asyncio.ensure_future(self.ensure_updated())
            return self.current_fee_rate
        except Exception as e:
            logger.error(f"Error getting fee rate: {str(e)}")
            return DEFAULT_FEE_RATE