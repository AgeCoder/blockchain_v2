import os
import random
import signal
import sys
import requests as req
from backend.app import create_app
from backend.wallet.wallet import Wallet
from backend.wallet.transaction import Transaction
from backend.wallet.transaction_pool import TransactionPool
from backend.blockchain.blockchain import Blockchain

app = create_app()
blockchain = app.config['BLOCKCHAIN']
transaction_pool = app.config['TX_POOL']
pubsub = app.config['PUBSUB']



ROOT_PORT = 5000
PORT = ROOT_PORT

def handle_shutdown(signal, frame):
    print("\nShutting down gracefully...")
    pubsub.pubnub.stop()
    sys.exit(0)

if os.environ.get('PEER') == 'True':
    PORT = random.randint(5001, 6000)
    try:
        result = req.get(f'http://localhost:{ROOT_PORT}/blockchain')
        result_blockchain = Blockchain.from_json(result.json())
        blockchain.replace_chain(result_blockchain.chain)
        print('Synced chain.')
    except Exception as e:
        print('Sync failed:', e)

if os.environ.get('SEED_DATA') == 'True':
    for _ in range(10):
        blockchain.add_block([
            Transaction(Wallet(), Wallet().address, random.randint(2, 50)).to_json(),
            Transaction(Wallet(), Wallet().address, random.randint(2, 50)).to_json()
        ])
    for _ in range(3):
        transaction_pool.set_transaction(
            Transaction(Wallet(), Wallet().address, random.randint(2, 50))
        )
signal.signal(signal.SIGINT, handle_shutdown)
app.run(port=PORT,debug=True)
