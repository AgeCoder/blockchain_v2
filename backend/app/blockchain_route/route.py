import time
import logging
from flask import jsonify, request
from backend.wallet.transaction import Transaction
from backend.config import BLOCK_SUBSIDY, HALVING_INTERVAL

def register_routes_blockchain(app):
    blockchain = app.config['BLOCKCHAIN']
    transaction_pool = app.config['TX_POOL']
    pubsub = app.config['PUBSUB']
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    @app.route('/blockchain', methods=['GET'])
    def route_blockchain():
        try:
            return jsonify(blockchain.to_json()), 200
        except Exception as e:
            logger.error(f"Error fetching blockchain: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/blockchain/range', methods=['GET'])
    def route_blockchain_range():
        try:
            start = max(0, int(request.args.get('start', 0)))
            end = min(len(blockchain.chain), int(request.args.get('end', 5)))
            if start >= end or start >= len(blockchain.chain):
                return jsonify({'error': 'Invalid range parameters'}), 400
            return jsonify(blockchain.to_json()['chain'][start:end]), 200
        except ValueError:
            return jsonify({'error': 'Invalid range parameters'}), 400
        except Exception as e:
            logger.error(f"Error fetching blockchain range: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/blockchain/length', methods=['GET'])
    def route_blockchain_length():
        try:
            return jsonify({'length': len(blockchain.chain)}), 200
        except Exception as e:
            logger.error(f"Error fetching blockchain length: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/blockchain/mine', methods=['POST'])
    def route_blockchain_mine():
        try:
            wallet = app.config.get('WALLET')
            if not wallet:
                return jsonify({'error': 'Miner wallet not initialized'}), 400

            transactions = transaction_pool.get_priority_transactions()
            total_fees = sum(tx.fee for tx in transactions)

            current_height = len(blockchain.chain)
            subsidy = BLOCK_SUBSIDY // (2 ** (current_height // HALVING_INTERVAL))
            coinbase_tx = Transaction.create_coinbase(
                miner_address=wallet.address,
                block_height=current_height + 1,
                total_fees=total_fees
            )

            block_data = [coinbase_tx] + transactions
            new_block = blockchain.add_block(block_data)

            pubsub.broadcast_block(new_block)
            transaction_pool.clear_blockchain_transactions(blockchain)

            return jsonify({
                'message': 'New block mined successfully',
                'block': new_block.to_json(),
                'reward': {
                    'subsidy': subsidy,
                    'fees': total_fees,
                    'total': subsidy + total_fees
                },
                'transactions': len(block_data),
                'difficulty': new_block.difficulty,
                'timestamp': time.time_ns()
            }), 200

        except Exception as e:
            logger.error(f"Mining error: {str(e)}")
            return jsonify({'error': f'Mining failed: {str(e)}'}), 500