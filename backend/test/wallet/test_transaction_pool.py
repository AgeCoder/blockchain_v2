from backend.wallet.transaction_pool import TransactionPool
from backend.wallet.wallet import Wallet
from backend.wallet.transaction import Transaction
from backend.blockchain.blockchain import Blockchain

def test_transaction_set():
    transaction_pool = TransactionPool()
    transaction = Transaction(Wallet(),'agecoder',108)
    transaction_pool.set_transaction(transaction)

    assert transaction_pool.transaction_map[transaction.id] == transaction


def test_clear_blockchain_transaction_pool():
    transaction_pool = TransactionPool()
    blockchain = Blockchain()

    transaction1 = Transaction(Wallet(),'agecoder',108)
    transaction2 = Transaction(Wallet(),'Randomcoder',108)
    
    transaction_pool.set_transaction(transaction1)
    transaction_pool.set_transaction(transaction2)
    
    blockchain.add_block([transaction1.to_json(),transaction2.to_json()])

    assert transaction1.id in transaction_pool.transaction_map
    assert transaction2.id in transaction_pool.transaction_map

    transaction_pool.clear_blockchain_transactions(blockchain)    

    assert not transaction1.id in transaction_pool.transaction_map
    assert not transaction2.id in transaction_pool.transaction_map
