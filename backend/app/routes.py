import time
from flask import  jsonify, request
from backend.wallet.transaction import Transaction
from backend.wallet.wallet import Wallet

def register_routes(app):
    blockchain = app.config['BLOCKCHAIN']

    @app.route('/')
    def route_home():
        return 'Welcome to DOP Blockchain'
    
    @app.route('/known-addresses')
    def route_known_addresses():
        known_addresses = set()

        for block in blockchain.chain:
            for transaction in block.data:
                known_addresses.update(transaction['output'].keys())
                
        return jsonify(list(known_addresses))

    

    
