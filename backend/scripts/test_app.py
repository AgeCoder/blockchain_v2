import requests as req
import time
from backend.wallet.wallet import Wallet

BASE_URL = 'http://127.0.0.1:5000'

def get_blockchain():
    return req.get(f'{BASE_URL}/blockchain').json()

def get_blockchain_mine():
    return req.get(f'{BASE_URL}/blockchain/mine').json()

def post_wallet_transact(recipient,amount):
    return req.post(f'{BASE_URL}/wallet/transact',json={'recipient' : recipient, 'amount' : amount})

def get_wallet_info():
    return req.get(f'{BASE_URL}/wallet/info').json()

start_blockchain = get_blockchain()
print(f'start_blockchain :  {start_blockchain}')

recipient = Wallet().address

post_wallet_transact_1 = post_wallet_transact(recipient,108)
print(f'\npost_wallet_transact_1: {post_wallet_transact_1}')

time.sleep(1)

post_wallet_transact_2 = post_wallet_transact(recipient,12)
print(f'\npost_wallet_transact_2: {post_wallet_transact_2}')

time.sleep(1)
mined_block = get_blockchain_mine()
print(f'mined_block : {mined_block}')

wallet_info = get_wallet_info()
print(f'wallet_info: {wallet_info}')