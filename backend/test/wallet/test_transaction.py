import pytest

from backend.wallet.transaction import Transaction
from backend.wallet.wallet import Wallet
from backend.config import MINING_REWARD , MINING_REWARD_INPUT

def test_transaction():
    sender_wallet = Wallet()
    recipient = 'recipient'
    amount = 108
    transaction = Transaction(sender_wallet,recipient,amount)

    assert transaction.output[recipient] == amount
    assert transaction.output[sender_wallet.address] == sender_wallet.balance - amount

    assert 'timestamp' in transaction.input
    assert transaction.input['amount'] == sender_wallet.balance
    assert transaction.input['address'] == sender_wallet.address
    assert transaction.input['public_key'] == sender_wallet.public_key

    assert Wallet.verify(
        transaction.input['public_key'],
        transaction.output,
        transaction.input['signature']
        )

def test_transaction_exceeds_balance():
    with pytest.raises(Exception,match='Amount Exceeds balance'):
        transaction = Transaction(Wallet(),'recipient',1008)

def test_transaction_update_exceeds_balance():
    sender_wallet = Wallet()
    transaction = Transaction(sender_wallet,'recipient',108)

    with pytest.raises(Exception,match='Amount Exceeds balance'):
        transaction.update(sender_wallet,'new_recipient',10008)

def test_transaction_update():
    sender_wallet = Wallet()
    first_recipient = 'first_recipient'
    first_amount = 108

    transaction = Transaction(sender_wallet,first_recipient,first_amount)

    next_recipient = 'next_recipient'
    next_amount = 108

    transaction.update(sender_wallet,next_recipient,next_amount)

    assert transaction.output[next_recipient] == next_amount
    assert transaction.output[sender_wallet.address] == sender_wallet.balance - first_amount - next_amount

    assert Wallet.verify(
        transaction.input['public_key'],
        transaction.output,
        transaction.input['signature']
        )
    
    to_first_recipient_again = 108
    transaction.update(sender_wallet,first_recipient,to_first_recipient_again)
    
    assert transaction.output[first_recipient] == first_amount + to_first_recipient_again
    assert transaction.output[sender_wallet.address] == sender_wallet.balance - first_amount - next_amount - to_first_recipient_again

    assert Wallet.verify(
        transaction.input['public_key'],
        transaction.output,
        transaction.input['signature']
        )

def test_is_vaild_transaction():
    Transaction.is_vaild(Transaction(Wallet(),'recipient',108))

def test_is_invaild_transaction():
    sender_wallet = Wallet()
    transaction = Transaction(sender_wallet,'recipient',108)
    transaction.output[sender_wallet.address] = 10008

    with pytest.raises(Exception,match='Invaild tranaction output values'):
        Transaction.is_vaild(transaction)

def test_is_invaild_transaction_with_invaild_signature():
    transaction = Transaction(Wallet(),'recipient',108)
    transaction.input['signature'] = Wallet().sign(transaction.output)

    with pytest.raises(Exception,match='Invaild signature'):
        Transaction.is_vaild(transaction)

def test_reward_transaction():
    miner_wallet = Wallet()
    transaction = Transaction.reward_transaction(miner_wallet)

    assert transaction.input == MINING_REWARD_INPUT
    assert transaction.output[miner_wallet.address] == MINING_REWARD

def test_vaild_reward_transaction():
    reward_transaction = Transaction.reward_transaction(Wallet())
    Transaction.is_vaild(reward_transaction)

def test_invaild_reward_transaction():
    reward_transaction = Transaction.reward_transaction(Wallet())
    reward_transaction.output['extra_recipient'] = 60

    with pytest.raises(Exception, match='Invaild Mining Reward Transaction'):
        Transaction.is_vaild(reward_transaction)

def test_invaild_reward_transaction_invalid_amount():
    miner_wallet = Wallet()
    reward_transaction = Transaction.reward_transaction(miner_wallet)
    reward_transaction.output[miner_wallet.address] = 7822900

    with pytest.raises(Exception, match='Invaild Mining Reward Transaction'):
        Transaction.is_vaild(reward_transaction)
