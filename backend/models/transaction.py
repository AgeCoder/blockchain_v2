import logging
import time
from uuid import uuid4
from typing import Dict, Optional
from core.config import (
    BLOCK_SUBSIDY, HALVING_INTERVAL, MINING_REWARD, MIN_FEE,
    MINING_REWARD_INPUT, BASE_TX_SIZE, DEFAULT_FEE_RATE
)
from models.wallet import Wallet

class Transaction:
    # Initializes a transaction with a single recipient, either coinbase or regular
    def __init__(self, sender_wallet=None, recipient=None, amount=None, id=None, 
                 output=None, input=None, fee=0, size=0, is_coinbase=False, fee_rate=DEFAULT_FEE_RATE):
        self.id = id or (f"coinbase_{str(uuid4())}" if is_coinbase else str(uuid4()))
        self.is_coinbase = is_coinbase
        self.fee = fee
        self.fee_rate = max(fee_rate, MIN_FEE / BASE_TX_SIZE)
        self.size = size or BASE_TX_SIZE
        self.recipient = recipient  # Single recipient address
        self.amount = amount  # Single amount
        self.recipients = [recipient] if recipient else []  # List to track recipients after updates
        self.amounts = {recipient: amount} if recipient and amount else {}  # Dict to track amounts
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

        try:
            if is_coinbase:
                if output is None or input is None:
                    raise ValueError("Coinbase transaction requires output and input")
                self.output = output
                self.input = input
            else:
                if not recipient or not amount or amount <= 0:
                    raise ValueError("Invalid transaction parameters")
                
                self.output = output or self._create_output(sender_wallet, recipient, amount)
                self.size = self._calculate_size()
                self.fee = max(self.size * self.fee_rate, MIN_FEE)
                
                if sender_wallet:  # Only calculate sender balance if wallet is provided
                    sender_balance = sender_wallet.calculate_balance(sender_wallet.blockchain, sender_wallet.address)
                    self.output[sender_wallet.address] = sender_balance - amount - self.fee
                    
                    if self.output[sender_wallet.address] < 0:
                        raise ValueError(f"Insufficient funds after fee: {self.output[sender_wallet.address]}")
                
                self.input = input or self._create_input(sender_wallet, self.output)
        except Exception as e:
            self.logger.error(f"Error initializing transaction: {str(e)}")
            raise

    # Creates the transaction output dictionary with single recipient initially
    def _create_output(self, sender_wallet, recipient: str, amount: float) -> Dict[str, float]:
        try:
            if not recipient or amount <= 0:
                raise ValueError("Invalid transaction parameters")
            
            if sender_wallet:
                available_balance = sender_wallet.calculate_balance(sender_wallet.blockchain, sender_wallet.address)
                if amount + self.fee > available_balance:
                    raise ValueError(f"Amount {amount} + fee {self.fee} exceeds balance {available_balance}")
                
                return {
                    recipient: amount,
                    sender_wallet.address: available_balance - amount - self.fee
                }
            else:
                # For validation during mining, use provided output or default
                return {recipient: amount}
        except Exception as e:
            self.logger.error(f"Error creating output: {str(e)}")
            raise

    # Creates the transaction input by selecting UTXOs and signing the output
    def _create_input(self, sender_wallet, output) -> Dict:
        try:
            if not sender_wallet:
                raise ValueError("Sender wallet required for input creation")
            
            required_amount = sum(output.values()) + self.fee
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
            
            return {
                'timestamp': time.time_ns(),
                'amount': total_input,
                'address': sender_wallet.address,
                'public_key': sender_wallet.public_key,  # PEM format
                'signature': sender_wallet.sign(output),
                'prev_tx_ids': [tx_id for tx_id, _ in selected_utxos]
            }
        except Exception as e:
            self.logger.error(f"Error creating input: {str(e)}")
            raise

    # Updates a pending transaction by adding a new recipient and adding to the fee rate
    def update(self, sender_wallet, recipient: str, amount: float, fee_rate=DEFAULT_FEE_RATE):
        try:
            if not sender_wallet or not recipient or amount <= 0 or fee_rate < 0:
                raise ValueError("Invalid transaction parameters")
            
            # Add new recipient and amount
            if recipient in self.amounts:
                self.amounts[recipient] += amount
            else:
                self.amounts[recipient] = amount
                self.recipients.append(recipient)
            
            self.output[recipient] = self.amounts[recipient]
            
            # Add the provided fee_rate to the existing fee_rate
            print(f"Adding fee rate: {fee_rate} to existing fee rate: {self.fee_rate}")
            self.fee_rate += fee_rate
            
            total_required = sum(self.amounts.values()) + self.fee
            
            available_balance = sender_wallet.calculate_balance(sender_wallet.blockchain, sender_wallet.address)
            if total_required > available_balance:
                raise ValueError(f"Insufficient funds: required {total_required}, available {available_balance}")
            
            # Adjust sender's balance for the updated amounts
            self.output[sender_wallet.address] = available_balance - total_required
            if self.output[sender_wallet.address] < 0:
                raise ValueError(f"Negative balance after update: {self.output[sender_wallet.address]}")
            
            self.input['signature'] = sender_wallet.sign(self.output)
            self.input['timestamp'] = time.time_ns()
        except Exception as e:
            self.logger.error(f"Error updating transaction: {str(e)}")
            raise

    # Calculates the transaction size in bytes, ensuring minimum size
    def _calculate_size(self) -> int:
        try:
            input_size = 0
            if hasattr(self, 'input') and self.input:
                input_size = sum(len(str(tx_id)) for tx_id in self.input.get('prev_tx_ids', []))
                input_size += len(str(self.input))
            output_size = len(str(self.output)) + sum(len(addr) for addr in self.recipients)
            return max(BASE_TX_SIZE, input_size + output_size)
        except Exception as e:
            self.logger.error(f"Error calculating size: {str(e)}")
            return BASE_TX_SIZE

    # Validates the transaction structure, signatures, and balances
    @staticmethod
    def is_valid(transaction) -> bool:
        try:
            if transaction.is_coinbase:
                outputs = list(transaction.output.items())
                block_height = transaction.input.get('block_height', 0)
                subsidy = BLOCK_SUBSIDY // (2 ** (block_height // HALVING_INTERVAL))
                total_fees = transaction.input.get('fees', 0)
                
                if len(outputs) != 1 or outputs[0][1] <= 0:
                    raise ValueError("Invalid coinbase transaction output")
                if outputs[0][1] > subsidy + total_fees:
                    print(f"Coinbase validation failed: output {outputs[0][1]}, subsidy {subsidy}, fees {total_fees}, block_height {block_height}")
                    raise ValueError(f"Coinbase output {outputs[0][1]} exceeds subsidy {subsidy} + fees {total_fees}")
                return True
            
            if transaction.input.get('address') == MINING_REWARD_INPUT['address']:
                if list(transaction.output.values()) != [MINING_REWARD]:
                    raise ValueError("Invalid mining reward transaction")
                return True
            
            output_total = sum(transaction.output.values())
            input_amount = transaction.input.get('amount', 0)
            if output_total < 0 or input_amount < 0 or transaction.fee < MIN_FEE:
                raise ValueError(f"Invalid values: output {output_total}, input {input_amount}, fee {transaction.fee}")
            if input_amount < output_total + transaction.fee:
                raise ValueError(f"Input amount {input_amount} insufficient for output {output_total} + fee {transaction.fee}")
            
            if not Wallet.verify(
                transaction.input['public_key'],
                transaction.output,
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

    # Creates a new coinbase transaction for miner rewards
    @staticmethod
    def create_coinbase(miner_address: str, block_height: int, total_fees: int = 0) -> 'Transaction':
        try:
            subsidy = BLOCK_SUBSIDY // (2 ** (block_height // HALVING_INTERVAL))
            total_reward = subsidy + total_fees
            if total_reward > subsidy + total_fees:
                print(f"Invalid coinbase reward: {total_reward} exceeds subsidy {subsidy} + fees {total_fees}")
                raise ValueError(f"Invalid coinbase reward: {total_reward} exceeds subsidy {subsidy} + fees {total_fees}")
            
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

    # Converts the transaction to a dictionary for serialization
    def to_json(self) -> Dict:
        try:
            return {
                'id': self.id,
                'input': self.input,
                'output': self.output,
                'fee': self.fee,
                'size': self.size,
                'is_coinbase': self.is_coinbase,
                'recipient': self.recipient,
                'amount': self.amount,
                'recipients': self.recipients,
                'amounts': self.amounts,
                'fee_rate': self.fee_rate
            }
        except Exception as e:
            self.logger.error(f"Error serializing transaction: {str(e)}")
            raise

    # Creates a transaction from a dictionary
    @classmethod
    def from_json(cls, transaction_dict: Dict) -> 'Transaction':
        try:
            is_coinbase = transaction_dict.get('is_coinbase', 
                transaction_dict.get('input', {}).get('address') == 'coinbase')
            return cls(
                id=transaction_dict['id'],
                output=transaction_dict['output'],
                input=transaction_dict['input'],
                fee=transaction_dict['fee'],
                size=transaction_dict['size'],
                is_coinbase=is_coinbase,
                recipient=transaction_dict.get('recipient'),
                amount=transaction_dict.get('amount'),
                fee_rate=transaction_dict.get('fee_rate', DEFAULT_FEE_RATE)
            )
        except Exception as e:
            logging.getLogger(__name__).error(f"Error deserializing transaction: {str(e)}")
            raise