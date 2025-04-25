import time
import logging
import json
from backend.utils.cryptohash import crypto_hash
from backend.config import MINRATE, BLOCK_SIZE_LIMIT, TARGET_BLOCK_TIME
from backend.utils.hex_to_binary import hex_to_binary
from backend.wallet.transaction import Transaction
from backend.config import BLOCK_SUBSIDY, HALVING_INTERVAL

GENESIS_DATA = {
    "data": [
        {
            "id": "genesis_initial_tx",
            "input": {
                "address": "coinbase",
                "block_height": 0,
                "coinbase_data": "Initial funding",
                "fees": 0,
                "public_key": "coinbase",
                "signature": "coinbase",
                "subsidy": 50,
                "timestamp": 1
            },
            "is_coinbase": True,
            "output": {
                "20b2ee470d526eda4b12": 50
            },
            "fee": 0,
            "size": 250
        }
    ],
    "difficulty": 3,
    "height": 0,
    "last_hash": "genesis_last_hash",
    "nonce": 0,
    "timestamp": 1,
    "tx_count": 1,
    "version": 1
}

GENESIS_DATA["merkle_root"] = crypto_hash(json.dumps(GENESIS_DATA["data"][0], sort_keys=True))
GENESIS_DATA["hash"] = crypto_hash(
    GENESIS_DATA["timestamp"],
    GENESIS_DATA["last_hash"],
    GENESIS_DATA["data"],
    GENESIS_DATA["difficulty"],
    GENESIS_DATA["nonce"],
    GENESIS_DATA["height"],
    GENESIS_DATA["version"],
    GENESIS_DATA["merkle_root"],
    GENESIS_DATA["tx_count"]
)

class Block:
    def __init__(self, timestamp, last_hash, hash, data, difficulty, nonce,
                 height=None, version=None, merkle_root=None, tx_count=None):
        try:
            self.timestamp = timestamp
            self.last_hash = last_hash
            self.hash = hash
            self.data = data
            self.difficulty = max(1, difficulty)
            self.nonce = nonce
            self.height = height if height is not None else 0
            self.version = version if version is not None else 1
            self.merkle_root = merkle_root if merkle_root is not None else self.calculate_merkle_root()
            self.tx_count = tx_count if tx_count is not None else len(data)

            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)

            self.validate_block()
        except Exception as e:
            self.logger.error(f"Error initializing block: {str(e)}")
            raise

    def validate_block(self):
        """Validate block properties."""
        if self.height < 0:
            raise ValueError("Block height cannot be negative")
        if self.difficulty < 1:
            raise ValueError("Block difficulty cannot be less than 1")
        if self.tx_count != len(self.data):
            raise ValueError("Transaction count does not match data length")

    def to_json(self):
        """Serialize block to JSON."""
        try:
            return {
                'timestamp': self.timestamp,
                'last_hash': self.last_hash,
                'hash': self.hash,
                'data': [tx if isinstance(tx, dict) else tx.to_json() for tx in self.data],
                'difficulty': self.difficulty,
                'nonce': self.nonce,
                'height': self.height,
                'version': self.version,
                'merkle_root': self.merkle_root,
                'tx_count': self.tx_count
            }
        except Exception as e:
            self.logger.error(f"Error serializing block: {str(e)}")
            raise

    @staticmethod
    def mine_block(last_block, data):
        """Mine a new block."""
        try:
            if not isinstance(last_block, Block):
                raise ValueError("Invalid last block")

            serialized_data = [tx.to_json() if not isinstance(tx, dict) else tx for tx in data]
            if len(str(serialized_data).encode('utf-8')) > BLOCK_SIZE_LIMIT:
                raise ValueError(f"Block data exceeds size limit of {BLOCK_SIZE_LIMIT} bytes")

            timestamp = time.time_ns()
            last_hash = last_block.hash
            difficulty = Block.adjust_difficulty(last_block, timestamp)
            nonce = 0
            height = last_block.height + 1
            version = 1
            merkle_root = Block.calculate_merkle_root(serialized_data)
            tx_count = len(data)

            hash = crypto_hash(
                timestamp, last_hash, serialized_data, difficulty, nonce, height, version, merkle_root, tx_count
            )

            while hex_to_binary(hash)[:difficulty] != '0' * difficulty:
                nonce += 1
                timestamp = time.time_ns()
                difficulty = Block.adjust_difficulty(last_block, timestamp)
                hash = crypto_hash(
                    timestamp, last_hash, serialized_data, difficulty, nonce, height, version, merkle_root, tx_count
                )

            return Block(
                timestamp, last_hash, hash, serialized_data, difficulty, nonce, height, version, merkle_root, tx_count
            )
        except Exception as e:
            logging.getLogger(__name__).error(f"Error mining block: {str(e)}")
            raise

    @staticmethod
    def calculate_merkle_root(data):
        """Calculate Merkle root for transactions."""
        try:
            if not data:
                return crypto_hash('')

            hashes = []
            for tx in data:
                tx_json = tx if isinstance(tx, dict) else tx.to_json()
                serialized_tx = json.dumps(tx_json, sort_keys=True, separators=(',', ':'), default=lambda x: f"{x:.4f}" if isinstance(x, float) else x)
                tx_hash = crypto_hash(serialized_tx)
                hashes.append(tx_hash)
                logging.getLogger(__name__).debug(f"Transaction hash: {tx_hash} for tx: {serialized_tx}")

            while len(hashes) > 1:
                temp = []
                for i in range(0, len(hashes), 2):
                    if i + 1 < len(hashes):
                        temp.append(crypto_hash(hashes[i] + hashes[i + 1]))
                    else:
                        temp.append(hashes[i])
                hashes = temp

            
            return hashes[0]
        except Exception as e:
            logging.getLogger(__name__).error(f"Error calculating Merkle root: {str(e)}")
            raise

    @staticmethod
    def genesis():
        """Create genesis block."""
        try:
            return Block(**GENESIS_DATA)
        except Exception as e:
            logging.getLogger(__name__).error(f"Error creating genesis block: {str(e)}")
            raise

    @staticmethod
    def from_json(block_json):
        """Deserialize block from JSON."""
        try:
            return Block(
                timestamp=block_json['timestamp'],
                last_hash=block_json['last_hash'],
                hash=block_json['hash'],
                data=block_json['data'],
                difficulty=block_json['difficulty'],
                nonce=block_json['nonce'],
                height=block_json.get('height', 0),
                version=block_json.get('version', 1),
                merkle_root=block_json.get('merkle_root', '0' * 64),
                tx_count=block_json.get('tx_count', len(block_json['data']))
            )
        except Exception as e:
            logging.getLogger(__name__).error(f"Error deserializing block: {str(e)}")
            raise

    @staticmethod
    def adjust_difficulty(last_block, new_timestamp):
        """Adjust mining difficulty."""
        try:
            time_diff = (new_timestamp - last_block.timestamp) / 1_000_000_000
            if time_diff < MINRATE:
                return last_block.difficulty + 1
            if last_block.difficulty > 1 and time_diff > TARGET_BLOCK_TIME * 2:
                return last_block.difficulty - 1
            return last_block.difficulty
        except Exception as e:
            logging.getLogger(__name__).error(f"Error adjusting difficulty: {str(e)}")
            return last_block.difficulty

    @staticmethod
    def is_valid_block(last_block, block):
        """Validate a block."""
        try:
            if not isinstance(last_block, Block) or not isinstance(block, Block):
                raise ValueError("Invalid block types")

            if block.last_hash != last_block.hash:
                raise ValueError("Last hash mismatch")

            if hex_to_binary(block.hash)[:block.difficulty] != '0' * block.difficulty:
                raise ValueError("Proof of work requirement not met")

            if abs(last_block.difficulty - block.difficulty) > 1:
                raise ValueError("Difficulty adjustment too large")

            if block.height != last_block.height + 1:
                raise ValueError("Invalid block height")

            calculated_merkle_root = Block.calculate_merkle_root(block.data)
            if block.merkle_root != calculated_merkle_root:
                raise ValueError(f"Invalid Merkle root: expected {calculated_merkle_root}, got {block.merkle_root}")

            if len(str(block.data).encode('utf-8')) > BLOCK_SIZE_LIMIT:
                raise ValueError(f"Block data exceeds size limit of {BLOCK_SIZE_LIMIT} bytes")

            reconstructed_hash = crypto_hash(
                block.timestamp, block.last_hash, block.data, block.difficulty, block.nonce,
                block.height, block.version, block.merkle_root, block.tx_count
            )

            if reconstructed_hash != block.hash:
                raise ValueError("Block hash mismatch")

            # Validate transactions
            coinbase_count = 0
            total_fees = 0.0
            coinbase_tx = None
            # First pass: collect fees from non-coinbase transactions
            for tx_json in block.data:
                tx = Transaction.from_json(tx_json)
                Transaction.is_valid(tx)
                if tx.is_coinbase:
                    coinbase_count += 1
                    if coinbase_count > 1:
                        raise ValueError("Multiple coinbase transactions")
                    coinbase_tx = tx
                else:
                    total_fees += tx.fee

            # Second pass: validate coinbase transaction with total fees
            if coinbase_tx:
                subsidy = BLOCK_SUBSIDY // (2 ** (block.height // HALVING_INTERVAL))
                total_output = sum(v for k, v in coinbase_tx.output.items())
                if total_output > subsidy + total_fees:
                    logging.getLogger(__name__).error(
                        f"Invalid coinbase output: {total_output} exceeds subsidy {subsidy} + fees {total_fees}"
                    )
                    raise ValueError(f"Invalid coinbase output: {total_output} exceeds {subsidy} + {total_fees}")

            if coinbase_count == 0 and block.height > 0:
                raise ValueError("Missing coinbase transaction")

        except Exception as e:
            logging.getLogger(__name__).error(f"Error validating block: {str(e)}")
            raise