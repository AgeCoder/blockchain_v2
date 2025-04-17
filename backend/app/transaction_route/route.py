from flask import  jsonify, request
import time

def register_routes_transaction(app):

    blockchain = app.config['BLOCKCHAIN']
    transaction_pool = app.config['TX_POOL']

    @app.route('/transaction')
    def route_transaction():
        return jsonify(transaction_pool.transaction_data())
        
    @app.route('/transactions/<string:address>')
    def route_transactions_by_address(address):
        transactions = []

        # Check transaction pool (pending transactions)
        for tx in transaction_pool.transaction_data():
            if (tx['input'].get('address') == address or 
                address in tx['output']):
                tx_data = {
                    'id': tx['id'],
                    'input': tx['input'],
                    'output': tx['output'],
                    'status': 'pending',
                    'timestamp': tx['input'].get('timestamp', time.time() * 1000000),  # Default to current time
                    'fee': tx.get('fee', 0)
                }
                transactions.append(tx_data)

        # Check blockchain (confirmed transactions)
        for block in blockchain.chain:
            for tx in block.data:
                if (tx['input'].get('address') == address or 
                    address in tx['output']):
                    tx_data = {
                        'id': tx['id'],
                        'input': tx['input'],
                        'output': tx['output'],
                        'status': 'confirmed',
                        'blockHeight': len(block.data),
                        'timestamp': tx['input'].get('timestamp', block.timestamp),  # Fallback to block timestamp
                        'fee': tx.get('fee', 0)
                    }
                    transactions.append(tx_data)

        # Sort by timestamp (newest first)
        transactions.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return jsonify(transactions)
