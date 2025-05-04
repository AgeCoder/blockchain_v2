import logging
from models.transaction import Transaction
from models.block import Block
from core.config import (
    BLOCK_SUBSIDY, HALVING_INTERVAL
)

class Blockchain:
    def __init__(self):
        self.chain = [Block.genesis()]
        self.utxo_set = {}
        self.current_height = 0
        self.difficulty_adjustment_blocks = []
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.initialize_utxo_set()

    def initialize_utxo_set(self):
        """Initialize the UTXO set from the genesis block."""
        try:
            self.utxo_set = {}
            genesis_block = self.chain[0]
            for tx_json in genesis_block.data:
                tx = Transaction.from_json(tx_json)
                if tx.output:
                    self.utxo_set[tx.id] = tx.output
                    self.logger.debug(f"Initialized UTXO for genesis tx {tx.id}: {tx.output}")
                else:
                    self.logger.warning(f"Genesis transaction {tx.id} has no outputs to add to UTXO set.")
        except Exception as e:
            self.logger.error(f"Error initializing UTXO set: {str(e)}")
            raise

    def add_block(self, transactions):
        """Add a new block to the chain and update the UTXO set."""
        try:
            last_block = self.chain[-1]
            serialized_transactions = [
                tx.to_json() if isinstance(tx, Transaction) else tx
                for tx in transactions
            ]
            for tx_json in serialized_transactions:
                tx = Transaction.from_json(tx_json)
                Transaction.is_valid(tx)
                if not tx.is_coinbase:
                    input_data = tx.input
                    if not (input_data and 'address' in input_data and 'prev_tx_ids' in input_data):
                        raise ValueError(f"Invalid transaction input format in tx {tx.id}: missing 'address' or 'prev_tx_ids'")
                    prev_tx_ids = input_data['prev_tx_ids']
                    input_address = input_data['address']
                    input_amount = input_data.get('amount', 0)
                    utxo_amount = 0
                    for prev_tx_id in prev_tx_ids:
                        if prev_tx_id not in self.utxo_set or input_address not in self.utxo_set[prev_tx_id]:
                            raise ValueError(f"Invalid transaction input: no UTXO found for tx {prev_tx_id} and address {input_address}")
                        utxo_amount += self.utxo_set[prev_tx_id].get(input_address, 0)
                    if input_amount > utxo_amount:
                        raise ValueError(f"Invalid transaction input: input amount {input_amount} exceeds UTXO amount {utxo_amount}")
            new_block = Block.mine_block(last_block, serialized_transactions)
            self.chain.append(new_block)
            self.current_height = new_block.height
            self.update_utxo_set(new_block)
            self.logger.info(f"Successfully added block {new_block.height} with hash {new_block.hash[:8]}...")
            return new_block
        except ValueError as ve:
            self.logger.error(f"Block {last_block.height + 1} REJECTED: {str(ve)}")
            raise
        except Exception as e:
            self.logger.error(f"Critical error adding block after {last_block.height}: {str(e)}")
            raise

    def update_utxo_set(self, block):
        """Update the UTXO set for a single block."""
        try:
            for tx_json in block.data:
                tx = Transaction.from_json(tx_json)
                if not tx.is_coinbase:
                    input_data = tx.input
                    if input_data and 'address' in input_data and 'prev_tx_ids' in input_data:
                        input_address = input_data['address']
                        prev_tx_ids = input_data['prev_tx_ids']
                        for prev_tx_id in prev_tx_ids:
                            if prev_tx_id in self.utxo_set and input_address in self.utxo_set[prev_tx_id]:
                                self.logger.debug(f"Spending UTXO from tx {prev_tx_id} for address {input_address} by tx {tx.id}")
                                del self.utxo_set[prev_tx_id]
                            else:
                                raise ValueError(f"Invalid transaction input: no UTXO found for tx {prev_tx_id} and address {input_address} in tx {tx.id}")
                    else:
                        raise ValueError(f"Invalid transaction input format in tx {tx.id}: missing 'address' or 'prev_tx_ids'")
                if tx.output:
                    if tx.id in self.utxo_set:
                        self.logger.warning(f"Duplicate transaction ID {tx.id} encountered in UTXO set. Overwriting.")
                    self.utxo_set[tx.id] = tx.output
                    self.logger.debug(f"Added new UTXO entry for tx {tx.id}: {tx.output}")
        except Exception as e:
            self.logger.error(f"Failed to update UTXO set for block {block.height}: {str(e)}")
            raise

    def rebuild_utxo_set(self, chain):
        """Rebuild the UTXO set from scratch for the given chain."""
        try:
            temp_utxo = {}
            for block in chain:
                for tx_json in block.data:
                    tx = Transaction.from_json(tx_json)
                    Transaction.is_valid(tx)
                    if not tx.is_coinbase:
                        input_data = tx.input
                        if not (input_data and 'address' in input_data and 'prev_tx_ids' in input_data):
                            raise ValueError(f"Invalid transaction input format in tx {tx.id}: missing 'address' or 'prev_tx_ids'")
                        input_address = input_data['address']
                        prev_tx_ids = input_data['prev_tx_ids']
                        for prev_tx_id in prev_tx_ids:
                            if prev_tx_id in temp_utxo:
                                self.logger.debug(f"Removing UTXO {prev_tx_id} for address {input_address} by tx {tx.id}")
                                temp_utxo.pop(prev_tx_id, None)
                            else:
                                raise ValueError(f"Invalid transaction input: no UTXO found for tx {prev_tx_id} and address {input_address} in tx {tx.id}")
                    if tx.output:
                        if tx.id in temp_utxo:
                            self.logger.warning(f"Duplicate transaction ID {tx.id} encountered during UTXO rebuild. Overwriting.")
                        temp_utxo[tx.id] = tx.output
                        self.logger.debug(f"Added UTXO for tx {tx.id}: {tx.output}")
            return temp_utxo
        except Exception as e:
            self.logger.error(f"Failed to rebuild UTXO set for chain of length {len(chain)}: {str(e)}")
            raise

    def replace_chain(self, chain):
        """Replace the current chain with a new chain and rebuild the UTXO set."""
        old_chain = self.chain[:]
        old_utxo_set = self.utxo_set.copy()
        try:
            if len(chain) <= len(self.chain):
                raise ValueError("New chain must be longer")
            Blockchain.is_valid_chain(chain)
            # Store current state for rollback in case of error
            old_chain = self.chain[:]
            old_utxo_set = self.utxo_set.copy()
            # Rebuild UTXO set for the new chain
            new_utxo_set = self.rebuild_utxo_set(chain)
            # If all validations pass, update the chain and UTXO set
            self.chain = chain
            self.utxo_set = new_utxo_set
            self.current_height = len(chain) - 1
            self.logger.info(f"Replaced chain with {self.current_height} blocks")
        except Exception as e:
            self.logger.error(f"Error replacing chain: {str(e)}")
            # Roll back to previous state
            self.chain = old_chain
            self.utxo_set = old_utxo_set
            raise

    def calculate_difficulty(self):
        """Calculate the mining difficulty based on recent blocks."""
        try:
            if len(self.difficulty_adjustment_blocks) < 2016:
                return self.chain[-1].difficulty
            first_block = self.difficulty_adjustment_blocks[0]
            last_block = self.difficulty_adjustment_blocks[-1]
            time_span = (last_block.timestamp - first_block.timestamp) / 1_000_000_000
            expected_time = 2016 * TARGET_BLOCK_TIME
            difficulty = first_block.difficulty * expected_time / max(time_span, 1)
            self.difficulty_adjustment_blocks = []
            return max(int(difficulty), 1)
        except Exception as e:
            self.logger.error(f"Error calculating difficulty: {str(e)}")
            return self.chain[-1].difficulty

    def to_json(self):
        """Serialize the blockchain to JSON."""
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
        """Deserialize a blockchain from JSON."""
        try:
            blockchain = Blockchain()
            blockchain.chain = [Block.from_json(block) for block in blockchain_json['chain']]
            blockchain.utxo_set = blockchain_json.get('utxo_set', {})
            blockchain.current_height = blockchain_json.get('current_height', len(blockchain.chain) - 1)
            blockchain.initialize_utxo_set()
            return blockchain
        except Exception as e:
            logging.getLogger(__name__).error(f"Error deserializing blockchain: {str(e)}")
            raise

    @staticmethod
    def is_valid_chain(chain):
        """Validate the entire chain."""
        try:
            if not chain or chain[0].to_json() != Block.genesis().to_json():
                raise ValueError("Invalid genesis block")
            utxo_set = {}
            total_subsidy = 0.0
            total_fees = 0.0
            expected_height = 0
            epsilon = 1e-6
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
                        subsidy = float(list(tx.output.values())[0])
                        fee = float(tx.input.get('fees', 0.0))
                        total_subsidy += subsidy
                        total_fees += fee
                    else:
                        input_data = tx.input
                        prev_tx_ids = input_data.get('prev_tx_ids', [])
                        for prev_tx_id in prev_tx_ids:
                            if prev_tx_id not in utxo_set:
                                raise ValueError(f"Invalid input for tx {tx.id}: UTXO {prev_tx_id} not found")
                            utxo_set.pop(prev_tx_id, None)
                    utxo_set[tx.id] = tx.output
                if not has_coinbase and i > 0:
                    raise ValueError("Missing coinbase transaction")
            expected_subsidy = float(Blockchain.calculate_total_subsidy(len(chain)))
            if abs(total_subsidy - (expected_subsidy + total_fees)) > epsilon:
                raise ValueError(f"Invalid total subsidy: got {total_subsidy:.4f}, expected {expected_subsidy:.4f} + fees {total_fees:.4f}")
        except Exception as e:
            logging.getLogger(__name__).error(f"Error validating chain: {str(e)}")
            raise

    @staticmethod
    def calculate_total_subsidy(block_count):

        """Calculate the total subsidy for the given number of blocks."""
        try:
            total = 0
            if block_count == 0:
                return total
            halvings = block_count // HALVING_INTERVAL
            for i in range(halvings + 1):
                blocks_in_period = min(HALVING_INTERVAL, block_count - i * HALVING_INTERVAL)
                subsidy = BLOCK_SUBSIDY // (2 ** i)
                total += blocks_in_period * subsidy
            return total
        except Exception as e:
            logging.getLogger(__name__).error(f"Error calculating subsidy: {str(e)}")
            raise
    
    