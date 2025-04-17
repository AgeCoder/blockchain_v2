from backend.blockchain.blockchain import Blockchain
from backend.blockchain.block import  GENESIS_DATA
from backend.wallet.transaction import Transaction
from backend.wallet.wallet import Wallet
import pytest 

def test_blockchain_instances():
    blockchain = Blockchain()
    assert blockchain.chain[0].hash == GENESIS_DATA['hash']
    
def test_add_block():
    blockchain = Blockchain()
    data = 'test_data'
    blockchain.add_block(data)

    assert blockchain.chain[-1].data == data

@pytest.fixture
def test_blockchain():
    blockchain = Blockchain()
    for i in range(3):
        blockchain.add_block([Transaction(Wallet(),'recipient',i).to_json()])
    
    return blockchain

def test_is_vaild_chain(test_blockchain):
    Blockchain.is_vaild_chain(test_blockchain.chain)
    

def  test_is_not_vaild_chain_bad_genesis(test_blockchain):
    test_blockchain.chain[0].hash = "00000000000000000changedData"

    with pytest.raises(Exception,match='Genesis Block Must be Vaild'):
        Blockchain.is_vaild_chain(test_blockchain.chain)

def test_replace_chain(test_blockchain):
    blockchain = Blockchain()
    blockchain.replace_chain(test_blockchain.chain)

    assert blockchain.chain == test_blockchain.chain

def test_replace_chain_not_longer(test_blockchain):
    blockchain = Blockchain()

    with pytest.raises(Exception , match='Cannot replace, The incoming chain must be longer'):
        test_blockchain.replace_chain(blockchain.chain)

def test_replace_chain_bad_chain(test_blockchain):
    blockchain = Blockchain()
    test_blockchain.chain[1].hash = '0000000000000000000changedhased'

    with pytest.raises(Exception , match='Cannot replace, The incoming chain must be vaild'):
        blockchain.replace_chain(test_blockchain.chain)

def test_vaild_transaction_chain(test_blockchain):
    test_blockchain.is_vaild_transaction_chain(test_blockchain.chain)

def test_vaild_transaction_chain_dupliacte_transaction(test_blockchain):
    transaction = Transaction(Wallet(),'recipient',1).to_json()
    test_blockchain.add_block([transaction,transaction])

    with pytest.raises(Exception, match='Transaction is not unique'):
        Blockchain.is_vaild_transaction_chain(test_blockchain.chain)

def test_vaild_transaction_chain_multiple_reward(test_blockchain):
    reward1 = Transaction.reward_transaction(Wallet()).to_json()
    reward2 = Transaction.reward_transaction(Wallet()).to_json()

    test_blockchain.add_block([reward1,reward2])

    with pytest.raises(Exception, match='There can only be one mining reward per Block.'):
        Blockchain.is_vaild_transaction_chain(test_blockchain.chain)

def test_vaild_transaction_chain_bad_transaction(test_blockchain):
    bad_transaction = Transaction(Wallet(),'recipient',1)
    bad_transaction.input['signature'] = Wallet().sign(bad_transaction.output)
    test_blockchain.add_block([bad_transaction.to_json()])

    with pytest.raises(Exception):
        Blockchain.is_vaild_transaction_chain(test_blockchain.chain)

def test_vaild_transaction_chain_bad_historic_balance(test_blockchain):
    wallet = Wallet()
    bad_transaction = Transaction(Wallet(),'recipient',1)
    bad_transaction.output[wallet.address] = 10008
    bad_transaction.input['amount'] = 10009
    bad_transaction.input['signature'] = wallet.sign(bad_transaction.output)

    test_blockchain.add_block([bad_transaction.to_json()])

    with pytest.raises(Exception,match='Transaction has an invalid amount'):
        Blockchain.is_vaild_transaction_chain(test_blockchain.chain)
