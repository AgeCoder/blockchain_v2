import logging
import time
from uuid import uuid4
from core.config import (
    BLOCK_SUBSIDY, HALVING_INTERVAL, MINING_REWARD, MIN_FEE,
    MINING_REWARD_INPUT, BASE_TX_SIZE, DEFAULT_FEE_RATE
)
from models.wallet import Wallet

class Transaction:
    def __init__(self, sender_wallet=None, recipient=None, amount=None, id=None, 
                 output=None, input=None, fee=0, size=0, is_coinbase=False, fee_rate=DEFAULT_FEE_RATE):
        self.id = id or (f"coinbase_{str(uuid4())}" if is_coinbase else str(uuid4()))
        self.is_coinbase = is_coinbase
        self.fee = fee
        self.size = size or BASE_TX_SIZE
        self.fee_rate = max(fee_rate, MIN_FEE / BASE_TX_SIZE)  # Ensure minimum fee rate
        self.recipient = recipient
        self.amount = amount
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        try:
            if is_coinbase:
                if output is None or input is None:
                    raise ValueError("Coinbase transaction requires output and input")
                self.output = output
                self.input = input
            else:
                if not sender_wallet or not recipient or amount <= 0:
                    raise ValueError("Invalid transaction parameters")
                self.output = output or self.create_output(sender_wallet, recipient, amount)
                self.input = input or self.create_input(sender_wallet, self.output)
                self.size = self.calculate_size()
                self.fee = max(self.size * self.fee_rate, MIN_FEE)
                # Recalculate output to account for dynamic fee
                self.output[sender_wallet.address] = (
                    sender_wallet.calculate_balance(sender_wallet.blockchain, sender_wallet.address)
                    - amount - self.fee
                )
                self.input = self.create_input(sender_wallet, self.output)
                if self.output[sender_wallet.address] < 0:
                    raise ValueError(f"Insufficient funds after fee: {self.output[sender_wallet.address]}")
        except Exception as e:
            self.logger.error(f"Error initializing transaction: {str(e)}")
            raise

    def create_output(self, sender_wallet, recipient, amount):
        try:
            available_balance = sender_wallet.calculate_balance(sender_wallet.blockchain, sender_wallet.address)
            if amount <= 0:
                raise ValueError("Amount must be positive")
            if amount + MIN_FEE > available_balance:
                raise ValueError(f"Amount {amount} + minimum fee {MIN_FEE} exceeds balance {available_balance}")
            output = {
                recipient: amount,
                sender_wallet.address: available_balance - amount - MIN_FEE  # Temporary fee placeholder
            }
            return output
        except Exception as e:
            self.logger.error(f"Error creating output: {str(e)}")
            raise

    def create_input(self, sender_wallet, output):
        try:
            available_balance = sender_wallet.calculate_balance(sender_wallet.blockchain, sender_wallet.address)
            required_amount = sum(v for k, v in output.items()) + self.fee
            if required_amount <= 0:
                raise ValueError("Required amount must be positive")
            selected_utxos = []
            total_input = 0
            for tx_id, outputs in sender_wallet.blockchain.utxo_set.items():
                for addr, amount in outputs.items():
                    if addr == sender_wallet.address:
                        if amount <= 0:
                            raise ValueError(f"Invalid UTXO amount: {amount}")
                        selected_utxos.append((tx_id, amount))
                        total_input += amount
                        if total_input >= required_amount:
                            break
                if total_input >= required_amount:
                    break
            if total_input < required_amount:
                raise ValueError(f"Insufficient funds: available {total_input}, required {required_amount}")
            if not selected_utxos:
                raise ValueError("No valid UTXOs found")
            # Define data to sign consistently
            
            input_data = {
                'timestamp': time.time_ns(),
                'amount': total_input,
                'address': sender_wallet.address,
                'public_key': sender_wallet.public_key,
                'signature': sender_wallet.sign(output),
                'prev_tx_ids': [tx_id for tx_id, _ in selected_utxos]
            }
            return input_data
        except Exception as e:
            self.logger.error(f"Error creating input: {str(e)}")
            raise

    def update(self, sender_wallet, recipient, amount, fee_rate=DEFAULT_FEE_RATE):
        try:
            self.fee_rate = max(fee_rate, MIN_FEE / self.size)
            self.size = self.calculate_size()
            new_fee = max(self.size * self.fee_rate, MIN_FEE)
            total_required = amount + new_fee
            available_balance = sender_wallet.calculate_balance(sender_wallet.blockchain, sender_wallet.address)
            if total_required > available_balance:
                raise ValueError(f"Insufficient funds: required {total_required}, available {available_balance}")
            if amount <= 0:
                raise ValueError("Amount must be positive")
            self.recipient = recipient
            self.amount = amount
            self.output[recipient] = amount
            self.output[sender_wallet.address] -= amount + (new_fee - self.fee)
            if self.output[sender_wallet.address] < 0:
                raise ValueError(f"Negative balance after update: {self.output[sender_wallet.address]}")
            self.fee = new_fee
            # Define data to sign consistently
            data_to_sign = {
                "sender": sender_wallet.address,
                "recipient": recipient,
                "amount": amount,
                "timestamp": time.time_ns(),
                "fee": self.fee
            }
            self.input['signature'] = sender_wallet.sign(data_to_sign)
            self.input['timestamp'] = time.time_ns()
        except Exception as e:
            self.logger.error(f"Error updating transaction: {str(e)}")
            raise

    def calculate_size(self):
        try:
            input_size = sum(len(str(tx_id)) for tx_id in self.input.get('prev_tx_ids', [])) + len(str(self.input))
            output_size = len(str(self.output))
            return max(BASE_TX_SIZE, input_size + output_size)
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
            if transaction.input.get('address') == MINING_REWARD_INPUT['address']:
                if list(transaction.output.values()) != [MINING_REWARD]:
                    raise ValueError("Invalid mining reward transaction")
                return True
            output_total = sum(v for k, v in transaction.output.items())
            input_amount = transaction.input.get('amount', 0)
            if output_total < 0 or input_amount < 0 or transaction.fee < MIN_FEE:
                raise ValueError(f"Invalid values: output {output_total}, input {input_amount}, fee {transaction.fee}")
            if input_amount < output_total + transaction.fee:
                raise ValueError(f"Invalid transaction: input {input_amount} < output {output_total} + fee {transaction.fee}")
            # Define data to verify consistently
            recipient = next((addr for addr in transaction.output if addr != transaction.input['address']), None)
            if not recipient:
                raise ValueError("No recipient found in output")
            data_to_verify = {
                "sender": transaction.input['address'],
                "recipient": recipient,
                "amount": transaction.amount,
                "timestamp": transaction.input['timestamp'],
                "fee": transaction.fee
            }
            if not Wallet.verify(
                transaction.input['public_key'],
                data_to_verify,
                transaction.input['signature']
            ):
                raise ValueError("Invalid signature")
            prev_tx_ids = transaction.input.get('prev_tx_ids', [])
            if not prev_tx_ids:
                raise ValueError("Transaction input missing prev_tx_ids")
            blockchain = transaction.input.get('blockchain') or getattr(transaction, 'blockchain', None)
            if blockchain:
                for tx_id in prev_tx_ids:
                    if tx_id not in blockchain.utxo_set:
                        raise ValueError(f"Invalid UTXO: {tx_id} not in UTXO set")
                    if transaction.input['address'] not in blockchain.utxo_set[tx_id]:
                        raise ValueError(f"UTXO {tx_id} does not belong to sender")
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
                'is_coinbase': self.is_coinbase,
                'fee_rate': self.fee_rate
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
                is_coinbase=is_coinbase,
                fee_rate=transaction_json.get('fee_rate', DEFAULT_FEE_RATE)
            )
        except Exception as e:
            logging.getLogger(__name__).error(f"Error deserializing transaction: {str(e)}")
            raise