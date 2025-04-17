import time
import logging
from backend.utils.cryptohash import crypto_hash
from backend.config import MINRATE, BLOCK_SIZE_LIMIT, TARGET_BLOCK_TIME
from backend.utils.hex_to_binary import hex_to_binary

GENESIS_DATA = {
    'timestamp': 1,
    'last_hash': 'genesis_last_hash',
    'hash': 'genesis_hash',
    'data': [],
    'difficulty': 3,
    'nonce': 0,
    'version': 1,
    'height': 0,
    'merkle_root': '0' * 64,
    'tx_count': 0
}

class Block:
    def __init__(self, timestamp, last_hash, hash, data, difficulty, nonce, 
                 height=None, version=None, merkle_root=None, tx_count=None):
        try:
            self.timestamp = timestamp
            self.last_hash = last_hash
            self.hash = hash
            self.data = data
            self.difficulty = max(1, difficulty)  # Ensure difficulty is at least 1
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
        """Validate block properties"""
        if self.height < 0:
            raise ValueError("Block height cannot be negative")
        if self.difficulty < 1:
            raise ValueError("Block difficulty cannot be less than 1")
        if self.tx_count != len(self.data):
            raise ValueError("Transaction count does not match data length")

    def __repr__(self):
        return (
            f'Block('
            f'timestamp: {self.timestamp}, '
            f'last_hash: {self.last_hash}, '
            f'hash: {self.hash}, '
            f'data: {self.data}, '
            f'difficulty: {self.difficulty}, '
            f'nonce: {self.nonce}, '
            f'height: {self.height}, '
            f'version: {self.version}, '
            f'merkle_root: {self.merkle_root}, '
            f'tx_count: {self.tx_count})'
        )

    def __eq__(self, other):
        try:
            if not isinstance(other, Block):
                return False
            return self.__dict__ == other.__dict__
        except Exception as e:
            self.logger.error(f"Error comparing blocks: {str(e)}")
            return False

    def to_json(self):
        try:
            return {
                'timestamp': self.timestamp,
                'last_hash': self.last_hash,
                'hash': self.hash,
                'data': self.data,
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
        try:
            if not isinstance(last_block, Block):
                raise ValueError("Invalid last block")
                
            # Validate block size
            serialized_data = str([str(item) for item in data])
            if len(serialized_data.encode('utf-8')) > BLOCK_SIZE_LIMIT:
                raise ValueError(f"Block data exceeds size limit of {BLOCK_SIZE_LIMIT} bytes")

            timestamp = time.time_ns()
            last_hash = last_block.hash
            difficulty = Block.adjust_difficulty(last_block, timestamp)
            nonce = 0
            height = last_block.height + 1
            version = 1
            merkle_root = Block.calculate_merkle_root(data)
            tx_count = len(data)

            hash = crypto_hash(
                timestamp, last_hash, data, difficulty, nonce, height, version, merkle_root, tx_count
            )

            while hex_to_binary(hash)[:difficulty] != '0' * difficulty:
                nonce += 1
                timestamp = time.time_ns()
                difficulty = Block.adjust_difficulty(last_block, timestamp)
                hash = crypto_hash(
                    timestamp, last_hash, data, difficulty, nonce, height, version, merkle_root, tx_count
                )

            return Block(
                timestamp, last_hash, hash, data, difficulty, nonce, height, version, merkle_root, tx_count
            )
        except Exception as e:
            logging.getLogger(__name__).error(f"Error mining block: {str(e)}")
            raise

    @staticmethod
    def calculate_merkle_root(data):
        """Calculate Merkle root using a binary tree approach"""
        try:
            if not data:
                return crypto_hash('')

            # Convert all data to hashes
            hashes = [crypto_hash(str(item)) for item in data]
            
            # Build Merkle tree
            while len(hashes) > 1:
                temp = []
                for i in range(0, len(hashes), 2):
                    if i + 1 < len(hashes):
                        temp.append(crypto_hash(hashes[i] + hashes[i + 1]))
                    else:
                        temp.append(hashes[i])  # Handle odd number of hashes
                hashes = temp

            return hashes[0]
        except Exception as e:
            logging.getLogger(__name__).error(f"Error calculating Merkle root: {str(e)}")
            raise

    @staticmethod
    def genesis():
        try:
            return Block(**GENESIS_DATA)
        except Exception as e:
            logging.getLogger(__name__).error(f"Error creating genesis block: {str(e)}")
            raise

    @staticmethod
    def from_json(block_json):
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
        try:
            time_diff = (new_timestamp - last_block.timestamp) / 1_000_000_000  # Convert ns to seconds
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
                
            if block.merkle_root != Block.calculate_merkle_root(block.data):
                raise ValueError("Invalid Merkle root")
                
            if len(str(block.data).encode('utf-8')) > BLOCK_SIZE_LIMIT:
                raise ValueError(f"Block data exceeds size limit of {BLOCK_SIZE_LIMIT} bytes")

            reconstructed_hash = crypto_hash(
                block.timestamp, block.last_hash, block.data, block.difficulty, block.nonce,
                block.height, block.version, block.merkle_root, block.tx_count
            )
            
            if reconstructed_hash != block.hash:
                raise ValueError("Block hash mismatch")
        except Exception as e:
            logging.getLogger(__name__).error(f"Error validating block: {str(e)}")
            raise

def main():
    try:
        # Test genesis block
        genesis_block = Block.genesis()
        print(f"Genesis Block: {genesis_block}")

        # Test mining a new block
        test_data = [{'id': 'tx1', 'amount': 10}, {'id': 'tx2', 'amount': 20}]
        new_block = Block.mine_block(genesis_block, test_data)
        print(f"Mined Block: {new_block}")

        # Test block validation
        Block.is_valid_block(genesis_block, new_block)
        print("Block validation successful")

        # Test invalid block
        invalid_block = Block(
            timestamp=new_block.timestamp,
            last_hash="invalid_hash",
            hash=new_block.hash,
            data=new_block.data,
            difficulty=new_block.difficulty,
            nonce=new_block.nonce,
            height=new_block.height,
            version=new_block.version,
            merkle_root=new_block.merkle_root,
            tx_count=new_block.tx_count
        )
        try:
            Block.is_valid_block(genesis_block, invalid_block)
        except ValueError as e:
            print(f"Expected error caught: {e}")

        # Test serialization
        block_json = new_block.to_json()
        deserialized_block = Block.from_json(block_json)
        print(f"Serialization test: {deserialized_block == new_block}")

    except Exception as e:
        logging.getLogger(__name__).error(f"Error in main: {str(e)}")
        print(f"Error: {e}")

if __name__ == '__main__':
    main()