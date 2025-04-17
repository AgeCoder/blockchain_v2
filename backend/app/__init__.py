from flask import Flask
from flask_cors import CORS
from backend.blockchain.blockchain import Blockchain
from backend.wallet.transaction_pool import TransactionPool
from backend.pubsub import PubSub
from backend.app.routes import register_routes
from backend.app.wallet.routes import register_routes_wallet
from backend.app.blockchain_route.route import register_routes_blockchain
from backend.app.transaction_route.route import register_routes_transaction

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r'/*': {'origins': '*'}})

    blockchain = Blockchain()
    transaction_pool = TransactionPool()
    pubsub = PubSub(blockchain, transaction_pool)

    # Store core components in app config
    app.config['BLOCKCHAIN'] = blockchain
    app.config['TX_POOL'] = transaction_pool
    app.config['PUBSUB'] = pubsub
    app.config['WALLET'] = None  # will be initialized per request

    # Register all routes
    register_routes(app)
    register_routes_wallet(app)
    register_routes_blockchain(app)
    register_routes_transaction(app)

    return app
