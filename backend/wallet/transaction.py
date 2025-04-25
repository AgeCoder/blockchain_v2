import time
import logging
from uuid import uuid4
from backend.config import MINING_REWARD, MINING_REWARD_INPUT, BLOCK_SUBSIDY, HALVING_INTERVAL, BASE_TX_SIZE
from backend.wallet.wallet import Wallet

class Transaction:
    def __init__(self, sender_wallet=None, recipient=None, amount=None, id=None, 
                 output=None, input=None, fee=0, size=0, is_coinbase=False):
        self.id = id or (f"coinbase_{str(uuid4())}" if is_coinbase else str(uuid4()))
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
            available_balance = sender_wallet.calculate_balance(sender_wallet.blockchain, sender_wallet.address)
            if amount + self.fee > available_balance:
                raise ValueError(f"Amount {amount} + fee {self.fee} exceeds balance {available_balance}")
            output = {
                recipient: amount,
                sender_wallet.address: available_balance - amount - self.fee
            }
            return output
        except Exception as e:
            self.logger.error(f"Error creating output: {str(e)}")
            raise

    def create_input(self, sender_wallet, output):
        try:
            available_balance = sender_wallet.calculate_balance(sender_wallet.blockchain, sender_wallet.address)
            required_amount = sum(v for k, v in output.items()) + self.fee
            selected_utxos = []
            total_input = 0
            # Collect UTXOs until sufficient funds are available
            for tx_id, outputs in sender_wallet.blockchain.utxo_set.items():
                for addr, amount in outputs.items():
                    if addr == sender_wallet.address:
                        selected_utxos.append((tx_id, amount))
                        total_input += amount
                        if total_input >= required_amount:
                            break
                if total_input >= required_amount:
                    break
            if total_input < required_amount:
                raise ValueError(f"Insufficient funds: available {total_input}, required {required_amount}")
            return {
                'timestamp': time.time_ns(),
                'amount': total_input,
                'address': sender_wallet.address,
                'public_key': sender_wallet.public_key,
                'signature': sender_wallet.sign(output),
                'prev_tx_ids': [tx_id for tx_id, _ in selected_utxos]  # Support multiple UTXOs
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
            self.input['timestamp'] = time.time_ns()
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
                block_height = transaction.input.get('block_height', 0)
                subsidy = BLOCK_SUBSIDY // (2 ** (block_height // HALVING_INTERVAL))
                total_fees = transaction.input.get('fees', 0)
                if len(outputs) != 1 or outputs[0][1] <= 0:
                    raise ValueError("Invalid coinbase transaction output")
                if outputs[0][1] > subsidy + total_fees:
                    raise ValueError(f"Coinbase output {outputs[0][1]} exceeds subsidy {subsidy} + fees {total_fees}")
                return True
            if transaction.input == MINING_REWARD_INPUT:
                if list(transaction.output.values()) != [MINING_REWARD]:
                    raise ValueError("Invalid mining reward transaction")
                return True
            output_total = sum(v for k, v in transaction.output.items())
            input_amount = transaction.input.get('amount', 0)
            if input_amount < output_total + transaction.fee:
                raise ValueError(f"Invalid transaction output values: input {input_amount} < output {output_total} + fee {transaction.fee}")
            if not Wallet.verify(
                transaction.input['public_key'],
                transaction.output,
                transaction.input['signature']
            ):
                raise ValueError("Invalid signature")
            prev_tx_ids = transaction.input.get('prev_tx_ids', [])
            if not prev_tx_ids:
                raise ValueError("Transaction input missing prev_tx_ids")
            return True
        except Exception as e:
            logging.getLogger(__name__).error(f"Error validating transaction: {str(e)}")
            raise

    @staticmethod
    def create_coinbase(miner_address, block_height, total_fees=0):
        try:
            subsidy = BLOCK_SUBSIDY // (2 ** (block_height // HALVING_INTERVAL))
            total_reward = subsidy + total_fees
            if total_reward <= 0:
                raise ValueError("Total reward must be positive")
            coinbase_input = {
                'timestamp': time.time_ns(),
                'address': 'coinbase',
                'public_key': 'coinbase',
                'signature': 'coinbase',
                'coinbase_data': f'Height:{block_height}',
                'block_height': block_height,
                'subsidy': subsidy,
                'fees': total_fees
            }
            output = {miner_address: total_reward}
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
                id=transaction_json['id'],
                output=transaction_json['output'],
                input=transaction_json['input'],
                fee=transaction_json['fee'],
                size=transaction_json['size'],
                is_coinbase=is_coinbase
            )
        except Exception as e:
            logging.getLogger(__name__).error(f"Error deserializing transaction: {str(e)}")
            raise