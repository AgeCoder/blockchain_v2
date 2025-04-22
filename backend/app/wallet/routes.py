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

            # Validate input
            if private_key_pem and not isinstance(private_key_pem, str):
                return jsonify({'error': 'Private key must be a string'}), 400
            if private_key_pem and not private_key_pem.strip():
                return jsonify({'error': 'Private key cannot be empty'}), 400

            # Normalize private key PEM format (add newlines if missing)
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

            # Initialize wallet
            wallet = None
            if private_key_pem:
                try:
                    # Deserialize private key and initialize wallet
                    private_key = Wallet.deserialize_private_key(None, private_key_pem)
                    wallet = Wallet(blockchain=blockchain, private_key=private_key)
                except ValueError as e:
                    app.logger.error(f"Invalid private key: {str(e)}")
                    return jsonify({'error': f'Invalid private key: {str(e)}'}), 400
            else:
                # Generate new wallet
                wallet = Wallet(blockchain=blockchain)

            # Save wallet instance in app config
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
            # 1. Validate wallet availability
            wallet = app.config.get('WALLET')
            if not wallet:
                return jsonify({'error': 'Wallet not initialized'}), 400

            # 2. Parse and validate request data
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

            # 3. Check for existing transaction in pool
            # transaction = transaction_pool.existing_transaction(wallet.address)

            # 4. Calculate dynamic fee
            estimated_size = BASE_TX_SIZE
            fee = max(fee_rate * estimated_size, MIN_FEE)

            # 5. Create or update transaction
            # if transaction:
            #     try:
            #         transaction.fee = fee
            #         transaction.update(wallet, recipient, amount)
            #     except Exception as e:
            #         app.logger.error(f"Transaction update failed: {str(e)}")
            #         return jsonify({'error': str(e)}), 400
            # else:
            try:
                transaction = Transaction(
                    sender_wallet=wallet,
                    recipient=recipient,
                    amount=amount,
                    fee=fee
                        )
            except Exception as e:
                    app.logger.error(f"Transaction creation failed: {str(e)}")
                    return jsonify({'error': str(e)}), 400

            # 6. Validate and broadcast using the synchronous wrapper
            Transaction.is_valid(transaction)
            pubsub.broadcast_transaction_sync(transaction)

            # 7. Return response
            return jsonify({
                'message': 'Transaction created successfully',
                'transaction': transaction.to_json(),
                'fee': transaction.fee,
                'size': transaction.size,
                'timestamp': time.time_ns()
            }), 200

        except ValueError as e:
            app.logger.error(f"Value error: {str(e)}")
            return jsonify({'error': f'Invalid numeric value: {str(e)}'}), 400
        except Exception as e:
            app.logger.error(f"Unexpected error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500