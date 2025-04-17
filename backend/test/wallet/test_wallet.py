from backend.wallet.wallet import Wallet
from backend.blockchain.blockchain import Blockchain
from backend.wallet.transaction import Transaction
from backend.config import STARTING_BALANCE

def test_verify_vaild_signature():
    data = { 'age' : 'coder'}
    wallet = Wallet()
    signature =  wallet.sign(data)
    assert Wallet.verify(wallet.public_key,data,signature)

def test_verify_Invaild_signature():
    data = { 'age' : 'evil_coder'}
    wallet = Wallet()
    signature =  wallet.sign(data)
    assert not Wallet.verify(Wallet().public_key,data,signature)


def test_calculate_balance():

    blockchain =  Blockchain()
    wallet = Wallet()

    assert Wallet.calculate_balance(blockchain,wallet.address) == STARTING_BALANCE

    amount = 108
    transaction = Transaction(wallet,'recipient',amount)
    blockchain.add_block([transaction.to_json()])

    assert Wallet.calculate_balance(blockchain,wallet.address) == STARTING_BALANCE - amount

    receiced_amount_1 = 108
    receiced_transaction_1 = Transaction( 
        Wallet(),
        wallet.address,
        receiced_amount_1
    )

    receiced_amount_2 = 108
    receiced_transaction_2 = Transaction( 
        Wallet(),
        wallet.address,
        receiced_amount_2
    )

    blockchain.add_block([receiced_transaction_1.to_json(),receiced_transaction_2.to_json()]
)
    assert Wallet.calculate_balance(blockchain,wallet.address) == STARTING_BALANCE - amount + (receiced_amount_1 + receiced_amount_2)

