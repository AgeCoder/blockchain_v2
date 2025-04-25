from flask import jsonify, request
from backend.wallet.wallet import Wallet
from backend.wallet.transaction import Transaction
import time
from backend.config import BASE_TX_SIZE, MIN_FEE, DEFAULT_FEE_RATE
import re

def register_routes_wallet(app):
    blockchain = app.config['BLOCKCHAIN']
    transaction_pool = app.config['TX_POOL']
    pubsub = app.config['PUBSUB']

    @app.route('/api/wallet', methods=['POST'])
    def init_wallet():
        try:
            data = request.get_json(silent=True)
            private_key_pem = data.get('private_key') if data else None

            if private_key_pem and not isinstance(private_key_pem, str):
                return jsonify({'error': 'Private key must be a string'}), 400
            if private_key_pem and not private_key_pem.strip():
                return jsonify({'error': 'Private key cannot be empty'}), 400

            if private_key_pem:
                private_key_pem = private_key_pem.strip()
                match = re.match(
                    r'-----BEGIN EC PRIVATE KEY-----(.*?)-----END EC PRIVATE KEY-----',
                    private_key_pem.replace('\n', ''),
                    re.DOTALL
                )
                if not match:
                    return jsonify({'error': 'Invalid private key format'}), 400
                key_content = match.group(1).strip()
                private_key_pem = (
                    f"-----BEGIN EC PRIVATE KEY-----\n"
                    f"{key_content}\n"
                    f"-----END EC PRIVATE KEY-----"
                )

            wallet = None
            if private_key_pem:
                try:
                    private_key = Wallet.deserialize_private_key(None, private_key_pem)
                    wallet = Wallet(blockchain=blockchain, private_key=private_key)
                except ValueError as e:
                    app.logger.error(f"Invalid private key: {str(e)}")
                    return jsonify({'error': f'Invalid private key: {str(e)}'}), 400
            else:
                wallet = Wallet(blockchain=blockchain)

            app.config['WALLET'] = wallet

            return jsonify({
                'message': 'Wallet initialized',
                'address': wallet.address,
                'publicKey': wallet.public_key,
                'privateKey': wallet.private_key_s,
                'balance': wallet.balance
            }), 200
        except Exception as e:
            app.logger.error(f"Error initializing wallet: {str(e)}")
            return jsonify({'error': f'Failed to initialize wallet: {str(e)}'}), 500

    @app.route('/wallet/info')
    def route_wallet_info():
        wallet = app.config.get('WALLET')
        if not wallet:
            return jsonify({'error': 'Wallet not initialized'}), 400

        return jsonify({
            'address': wallet.address,
            'balance': wallet.balance,
            'publicKey': wallet.public_key,
            'privateKey': wallet.private_key_s
        })

    @app.route('/wallet/transact', methods=['POST'])
    def route_wallet_transact():
        try:
            wallet = app.config.get('WALLET')
            if not wallet:
                return jsonify({'error': 'Wallet not initialized'}), 400

            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid JSON data'}), 400

            recipient = data.get('recipient')
            amount = float(data.get('amount')) if data.get('amount') else None
            fee_rate = float(data.get('fee', DEFAULT_FEE_RATE))

            if not recipient or not amount:
                return jsonify({'error': 'Missing recipient or amount'}), 400
            if amount <= 0:
                return jsonify({'error': 'Amount must be positive'}), 400
            if recipient == wallet.address:
                return jsonify({'error': 'Cannot send to self'}), 400

            blockchain = app.config.get('BLOCKCHAIN')
            transaction_pool = app.config.get('TX_POOL')
            pubsub = app.config.get('PUBSUB')
            if not blockchain or not transaction_pool or not pubsub:
                return jsonify({'error': 'Blockchain, transaction pool, or PubSub not initialized'}), 400

            estimated_size = BASE_TX_SIZE
            fee = max(fee_rate * estimated_size, MIN_FEE)

            confirmed_balance = wallet.calculate_balance(blockchain, wallet.address)
            pending_txs = [tx for tx in transaction_pool.transaction_map.values() 
                          if tx.input.get('address') == wallet.address]
            total_pending_spend = sum(
                sum(v for k, v in tx.output.items() if k != wallet.address) + tx.fee
                for tx in pending_txs
            )
            available_balance = confirmed_balance - total_pending_spend

            total_cost = amount + fee
            if total_cost > available_balance:
                error_msg = (
                    f"Insufficient funds. Available: {available_balance:.4f} COIN, "
                    f"Required: {total_cost:.4f} COIN (Amount: {amount:.4f} + Fee: {fee:.4f}). "
                    f"Pending transactions: {len(pending_txs)}"
                )
                return jsonify({'error': error_msg}), 400

            try:
                transaction = Transaction(
                    sender_wallet=wallet,
                    recipient=recipient,
                    amount=amount,
                    fee=fee
                )
            except Exception as e:
                app.logger.error(f"Transaction creation/update failed: {str(e)}")
                return jsonify({'error': str(e)}), 400

            try:
                Transaction.is_valid(transaction)
                transaction_pool.set_transaction(transaction)
            except Exception as e:
                app.logger.error(f"Transaction validation failed: {str(e)}")
                return jsonify({'error': f'Invalid transaction rw159: {str(e)}'}), 400

            try:
                pubsub.broadcast_transaction_sync(transaction)
            except Exception as e:
                app.logger.error(f"Broadcast failed: {str(e)}")
                transaction_pool.transaction_map.pop(transaction.id, None)
                return jsonify({'error': f'Broadcast failed: {str(e)}'}), 500

            return jsonify({
                'message': 'Transaction created successfully',
                'transaction': transaction.to_json(),
                'fee': transaction.fee,
                'size': transaction.size,
                'timestamp': time.time_ns(),
                'balance_info': {
                    'confirmed_balance': confirmed_balance,
                    'pending_spend': total_pending_spend + total_cost,
                    'available_balance': available_balance - total_cost
                }
            }), 200
        except ValueError as e:
            app.logger.error(f"Value error: {str(e)}")
            return jsonify({'error': f'Invalid numeric value: {str(e)}'}), 400
        except Exception as e:
            app.logger.error(f"Unexpected error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500