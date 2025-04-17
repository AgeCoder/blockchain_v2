import time
import logging
from backend.blockchain.block import Block
from backend.wallet.transaction import Transaction
from backend.config import BLOCK_SUBSIDY, HALVING_INTERVAL, TARGET_BLOCK_TIME

class Blockchain:
    def __init__(self):
        self.chain = [Block.genesis()]
        self.utxo_set = {}
        self.current_height = 0
        self.difficulty_adjustment_blocks = []
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def add_block(self, transactions):
        try:
            last_block = self.chain[-1]
            serialized_transactions = [
                tx.to_json() if isinstance(tx, Transaction) else tx
                for tx in transactions
            ]
            
            new_block = Block.mine_block(last_block, serialized_transactions)
            self.update_utxo_set(new_block)
            self.chain.append(new_block)
            self.current_height += 1
            self.difficulty_adjustment_blocks.append(new_block)
            
            return new_block
        except Exception as e:
            self.logger.error(f"Error adding block: {str(e)}")
            raise

    def update_utxo_set(self, block):
        try:
            for tx_json in block.data:
                tx = Transaction.from_json(tx_json)
                
                if not tx.is_coinbase:
                    input_data = tx.input
                    if input_data and 'transaction_id' in input_data:
                        self.utxo_set.pop(input_data['transaction_id'], None)
                
                self.utxo_set[tx.id] = tx.output
        except Exception as e:
            self.logger.error(f"Error updating UTXO set: {str(e)}")
            raise

    def replace_chain(self, chain):
        try:
            if len(chain) <= len(self.chain):
                raise ValueError("New chain must be longer")

            Blockchain.is_valid_chain(chain)
            
            temp_utxo = self.utxo_set.copy()
            for block in chain[len(self.chain):]:
                for tx_json in block.data:
                    tx = Transaction.from_json(tx_json)
                    if not tx.is_coinbase:
                        for input_data in [tx.input] if tx.input else []:
                            if input_data.get('transaction_id') not in temp_utxo:
                                raise ValueError(f"Input {input_data['transaction_id']} not found")
                            temp_utxo.pop(input_data['transaction_id'])
                    temp_utxo[tx.id] = tx.output

            self.chain = chain
            self.utxo_set = temp_utxo
            self.current_height = len(chain) - 1
        except Exception as e:
            self.logger.error(f"Error replacing chain: {str(e)}")
            raise

    def calculate_difficulty(self):
        try:
            if len(self.difficulty_adjustment_blocks) < 2016:
                return self.chain[-1].difficulty

            first_block = self.difficulty_adjustment_blocks[0]
            last_block = self.difficulty_adjustment_blocks[-1]
            
            time_span = (last_block.timestamp - first_block.timestamp) / 1_000_000_000  # Convert ns to s
            expected_time = 2016 * TARGET_BLOCK_TIME
            
            difficulty = first_block.difficulty * expected_time / max(time_span, 1)
            self.difficulty_adjustment_blocks = []
            
            return max(int(difficulty), 1)
        except Exception as e:
            self.logger.error(f"Error calculating difficulty: {str(e)}")
            return self.chain[-1].difficulty

    def to_json(self):
        try:
            return {
                'chain': [block.to_json() for block in self.chain],
                'utxo_set': self.utxo_set,
                'current_height': self.current_height
            }
        except Exception as e:
            self.logger.error(f"Error serializing blockchain: {str(e)}")
            raise

    @staticmethod
    def from_json(blockchain_json):
        try:
            blockchain = Blockchain()
            blockchain.chain = [Block.from_json(block) for block in blockchain_json['chain']]
            blockchain.utxo_set = blockchain_json.get('utxo_set', {})
            blockchain.current_height = blockchain_json.get('current_height', len(blockchain.chain) - 1)
            return blockchain
        except Exception as e:
            logging.getLogger(__name__).error(f"Error deserializing blockchain: {str(e)}")
            raise

    @staticmethod
    def is_valid_chain(chain):
        try:
            if not chain or chain[0] != Block.genesis():
                raise ValueError("Invalid genesis block")

            utxo_set = {}
            total_subsidy = 0
            expected_height = 0

            for i, block in enumerate(chain):
                if i > 0:
                    Block.is_valid_block(chain[i-1], block)
                
                if block.height != expected_height:
                    raise ValueError(f"Incorrect height at block {i}")
                
                expected_height += 1
                has_coinbase = False
                
                for tx_json in block.data:
                    tx = Transaction.from_json(tx_json)
                    Transaction.is_valid(tx)
                    
                    if tx.is_coinbase:
                        if has_coinbase:
                            raise ValueError("Multiple coinbase transactions")
                        has_coinbase = True
                        total_subsidy += list(tx.output.values())[0]
                    else:
                        input_data = tx.input
                        if input_data and input_data.get('transaction_id') not in utxo_set:
                            raise ValueError(f"Input {input_data['transaction_id']} not found")
                        utxo_set.pop(input_data['transaction_id'], None)
                    
                    utxo_set[tx.id] = tx.output

                if not has_coinbase and i > 0:
                    raise ValueError("Missing coinbase transaction")

            expected_subsidy = Blockchain.calculate_total_subsidy(len(chain))
            if total_subsidy > expected_subsidy:
                raise ValueError("Invalid total subsidy")
        except Exception as e:
            logging.getLogger(__name__).error(f"Error validating chain: {str(e)}")
            raise

    @staticmethod
    def calculate_total_subsidy(block_count):
        try:
            total = 0
            halvings = block_count // HALVING_INTERVAL
            
            for i in range(halvings + 1):
                blocks_in_period = min(HALVING_INTERVAL, block_count - i * HALVING_INTERVAL)
                subsidy = BLOCK_SUBSIDY // (2 ** i)
                total += blocks_in_period * subsidy
            
            return total
        except Exception as e:
            logging.getLogger(__name__).error(f"Error calculating subsidy: {str(e)}")
            raise