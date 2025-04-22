import logging
from backend.wallet.transaction import Transaction

class TransactionPool:
    def __init__(self):
        self.transaction_map = {}
        logging.basicConfig(level=logging.DEBUG)  # More verbose logging
        self.logger = logging.getLogger(__name__)

    def set_transaction(self, transaction):
        try:
            self.logger.debug(f"Attempting to add transaction {transaction.id} to pool")
            if not isinstance(transaction, Transaction):
                raise ValueError("Invalid transaction type")
            
            Transaction.is_valid(transaction)
            
            if transaction.id in self.transaction_map:
                self.logger.warning(f"Transaction {transaction.id} already in pool")
                return
            
            self.transaction_map[transaction.id] = transaction
            self.logger.info(f"Successfully added transaction {transaction.id} to pool")
        except Exception as e:
            self.logger.error(f"Failed to add transaction {transaction.id}: {str(e)}")
            raise

    def existing_transaction(self, address):
        try:
            for transaction in self.transaction_map.values():
                if transaction.input.get('address') == address:
                    return transaction
            return None
        except Exception as e:
            self.logger.error(f"Error checking existing transaction: {str(e)}")
            return None

    def transaction_data(self):
        try:
            return [transaction.to_json() for transaction in self.transaction_map.values()]
        except Exception as e:
            self.logger.error(f"Error getting transaction data: {str(e)}")
            return []

    def clear_blockchain_transactions(self, blockchain):
        try:
            for block in blockchain.chain:
                for transaction in block.data:
                    if isinstance(transaction, dict) and 'id' in transaction:
                        self.transaction_map.pop(transaction['id'], None)
        except Exception as e:
            self.logger.error(f"Error clearing transactions: {str(e)}")

    def get_priority_transactions(self):
        try:
            return sorted(
                self.transaction_map.values(),
                key=lambda tx: tx.fee if hasattr(tx, 'fee') else 0,
                reverse=True
            )
        except Exception as e:
            self.logger.error(f"Error getting priority transactions: {str(e)}")
            return []

    def to_json(self):
        try:
            return {
                'transactions': self.transaction_data(),
                'count': len(self.transaction_map)
            }
        except Exception as e:
            self.logger.error(f"Error serializing transaction pool: {str(e)}")
            return {}