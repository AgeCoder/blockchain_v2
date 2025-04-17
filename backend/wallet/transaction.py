import time
import logging
from uuid import uuid4
from backend.config import MINING_REWARD, MINING_REWARD_INPUT, BLOCK_SUBSIDY, HALVING_INTERVAL, BASE_TX_SIZE
from backend.wallet.wallet import Wallet

class Transaction:
    def __init__(self, sender_wallet=None, recipient=None, amount=None, id=None, 
                 output=None, input=None, fee=0, size=0, is_coinbase=False):
        self.id = id or (f"coinbase_{str(uuid4())[:8]}" if is_coinbase else str(uuid4())[:8])
        self.is_coinbase = is_coinbase
        self.fee = fee
        self.size = size or BASE_TX_SIZE
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        try:
            if is_coinbase:
                self.output = output
                self.input = input
            else:
                self.output = output or self.create_output(sender_wallet, recipient, amount)
                self.input = input or self.create_input(sender_wallet, self.output)
        except Exception as e:
            self.logger.error(f"Error initializing transaction: {str(e)}")
            raise

    def create_output(self, sender_wallet, recipient, amount):
        try:
            if not sender_wallet or not recipient or amount <= 0:
                raise ValueError("Invalid transaction parameters")
                
            if amount + self.fee > sender_wallet.balance:
                raise ValueError("Amount + fee exceeds balance")

            return {
                recipient: amount,
                sender_wallet.address: sender_wallet.balance - amount - self.fee,
                'fee': self.fee
            }
        except Exception as e:
            self.logger.error(f"Error creating output: {str(e)}")
            raise

    def create_input(self, sender_wallet, output):
        try:
            return {
                'timestamp': time.time_ns(),
                'amount': sender_wallet.balance,
                'address': sender_wallet.address,
                'public_key': sender_wallet.public_key,
                'signature': sender_wallet.sign(output)
            }
        except Exception as e:
            self.logger.error(f"Error creating input: {str(e)}")
            raise

    def update(self, sender_wallet, recipient, amount):
        try:
            if amount <= 0:
                raise ValueError("Invalid amount")
                
            available = self.output.get(sender_wallet.address, 0)
            if amount > available:
                raise ValueError("Amount exceeds available balance")

            self.output[recipient] = self.output.get(recipient, 0) + amount
            self.output[sender_wallet.address] -= amount
            self.input = self.create_input(sender_wallet, self.output)
            self.size = self.calculate_size()
        except Exception as e:
            self.logger.error(f"Error updating transaction: {str(e)}")
            raise

    def calculate_size(self):
        try:
            return len(str(self.output)) + len(str(self.input)) + BASE_TX_SIZE
        except Exception as e:
            self.logger.error(f"Error calculating size: {str(e)}")
            return BASE_TX_SIZE

    @staticmethod
    def is_valid(transaction):
        try:
            if transaction.is_coinbase:
                outputs = list(transaction.output.items())
                if len(outputs) != 1 or outputs[0][1] <= 0:
                    raise ValueError("Invalid coinbase transaction output")
                return True

            if transaction.input == MINING_REWARD_INPUT:
                if list(transaction.output.values()) != [MINING_REWARD]:
                    raise ValueError("Invalid mining reward transaction")
                return True

            output_total = sum(v for k, v in transaction.output.items() if k != 'fee')
            if transaction.input['amount'] != output_total + transaction.output.get('fee', 0):
                raise ValueError("Invalid transaction output values")

            if not Wallet.verify(
                transaction.input['public_key'],
                transaction.output,
                transaction.input['signature']
            ):
                raise ValueError("Invalid signature")
                
            return True
        except Exception as e:
            logging.getLogger(__name__).error(f"Error validating transaction: {str(e)}")
            raise

    @staticmethod
    def create_coinbase(miner_address, block_height, total_fees=0):
        try:
            subsidy = BLOCK_SUBSIDY // (2 ** (block_height // HALVING_INTERVAL))
            total_reward = subsidy + total_fees

            coinbase_input = {
                'timestamp': time.time_ns(),
                'address': 'coinbase',
                'public_key': 'coinbase',
                'signature': 'coinbase',
                'coinbase_data': f'Height:{block_height}',
                'block_height': block_height
            }

            output = {
                miner_address: total_reward,
                'subsidy': subsidy,
                'fees': total_fees
            }

            return Transaction(
                input=coinbase_input,
                output=output,
                fee=0,
                size=BASE_TX_SIZE,
                is_coinbase=True
            )
        except Exception as e:
            logging.getLogger(__name__).error(f"Error creating coinbase: {str(e)}")
            raise

    def to_json(self):
        try:
            return {
                'id': self.id,
                'input': self.input,
                'output': self.output,
                'fee': self.fee,
                'size': self.size,
                'is_coinbase': self.is_coinbase
            }
        except Exception as e:
            self.logger.error(f"Error serializing transaction: {str(e)}")
            raise

    @staticmethod
    def from_json(transaction_json):
        try:
            is_coinbase = transaction_json.get('is_coinbase', 
                transaction_json.get('input', {}).get('address') == 'coinbase')
                
            return Transaction(
                id=transaction_json.get('id'),
                output=transaction_json.get('output'),
                input=transaction_json.get('input'),
                fee=transaction_json.get('fee', 0),
                size=transaction_json.get('size', BASE_TX_SIZE),
                is_coinbase=is_coinbase
            )
        except Exception as e:
            logging.getLogger(__name__).error(f"Error deserializing transaction: {str(e)}")
            raise