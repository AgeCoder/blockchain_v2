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

    @app.route('/mine', methods=['POST'])
    def route_mine():
        try:
            wallet = app.config.get('WALLET')
            blockchain = app.config.get('BLOCKCHAIN')
            transaction_pool = app.config.get('TX_POOL')
            pubsub = app.config.get('PUBSUB')
            if not wallet or not blockchain or not transaction_pool or not pubsub:
                return jsonify({'error': 'Blockchain, transaction pool, wallet, or PubSub not initialized'}), 400
            transactions = transaction_pool.get_priority_transactions()[:10]
            valid_transactions = []
            for tx in transactions:
                try:
                    Transaction.is_valid(tx)
                    valid_transactions.append(tx)
                except Exception as e:
                    app.logger.warning(f"Invalid transaction {tx.id} skipped: {str(e)}")
                    
            total_fees = sum(tx.fee for tx in valid_transactions)
            coinbase_tx = Transaction.create_coinbase(wallet.address, blockchain.current_height + 1, total_fees)
            all_transactions = [coinbase_tx] + valid_transactions
            new_block = blockchain.add_block(all_transactions)
            transaction_pool.clear_blockchain_transactions(blockchain)
            pubsub.broadcast_block_sync(new_block)
            confirmed_balance = wallet.calculate_balance(blockchain, wallet.address)
            return jsonify({
                'message': 'Block mined successfully',
                'block': new_block.to_json(),
                'reward': coinbase_tx.output[wallet.address],
                'confirmed_balance': confirmed_balance
            }), 200
        except Exception as e:
            app.logger.error(f"Unexpected error in mining: {str(e)}")
            return jsonify({'error': str(e)}), 500