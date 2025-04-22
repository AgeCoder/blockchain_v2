import asyncio
import threading
import signal
import sys
import os
import random
import requests as req
import logging
from flask import Flask
from flask_cors import CORS
from backend.blockchain.blockchain import Blockchain
from backend.wallet.transaction_pool import TransactionPool
from backend.p2p import PubSub
from backend.app.routes import register_routes
from backend.app.wallet.routes import register_routes_wallet
from backend.app.blockchain_route.route import register_routes_blockchain
from backend.app.transaction_route.route import register_routes_transaction
from backend.wallet.wallet import Wallet
from backend.wallet.transaction import Transaction
from backend.p2p import get_public_ip

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ROOT_PORT = 5000

def create_app(blockchain_instance: Blockchain, transaction_pool_instance: TransactionPool, pubsub_instance: PubSub) -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r'/*': {'origins': '*'}})

    app.config['BLOCKCHAIN'] = blockchain_instance
    app.config['TX_POOL'] = transaction_pool_instance
    app.config['PUBSUB'] = pubsub_instance
    app.config['WALLET'] = None

    register_routes(app)
    register_routes_wallet(app)
    register_routes_blockchain(app)
    register_routes_transaction(app)

    return app

def run_flask_server(flask_app: Flask, port: int):
    try:
        logger.info("Starting Flask app on port %s...", port)
        flask_app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
    except Exception as e:
        logger.error("Error starting Flask app: %s", e)

def handle_shutdown(sig, frame):
    logger.info(f"Shutdown signal ({sig}) received. Initiating graceful shutdown...")
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            logger.info("Stopping asyncio event loop...")
            loop.call_soon_threadsafe(loop.stop)
        else:
            logger.info("Asyncio event loop not running or already stopped.")
    except Exception as e:
        logger.error(f"Error during shutdown handling: {e}")



if __name__ == "__main__":
    blockchain = Blockchain()
    transaction_pool = TransactionPool()
    #for testing purposes
    is_peer = os.environ.get('PEER') == 'True'
    os.environ['HOST'] = os.environ.get('HOST', get_public_ip())
    
    if is_peer:
        PORT = 4000
    else:
        PORT = ROOT_PORT

    pubsub = PubSub(blockchain, transaction_pool)
    app = create_app(blockchain, transaction_pool, pubsub)

    

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        loop = asyncio.get_running_loop()
        logger.info("Using existing asyncio event loop.")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("Created and set a new asyncio event loop.")

    pubsub.loop = loop
    logger.info(f"PubSub instance configured with asyncio loop: {pubsub.loop}")

    flask_app_port = PORT
    logger.info(f"Starting Flask app in a separate thread on port {flask_app_port}...")
    flask_thread = threading.Thread(target=run_flask_server, args=(app, flask_app_port), daemon=True)
    flask_thread.start()
    logger.info("Flask thread started.")

    logger.info("Starting WebSocket server and peer discovery tasks in the asyncio loop...")
    try:
        websocket_server_task = loop.create_task(pubsub.start_server())
        peer_discovery_task = loop.create_task(pubsub.run_peer_discovery())

        logger.info("Asyncio event loop running forever, managing WebSocket server and peer discovery...")
        loop.run_forever()

    except KeyboardInterrupt:
        logger.info("Asyncio loop stopped by KeyboardInterrupt.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during asyncio loop execution: {e}")

    finally:
        logger.info("Asyncio loop has stopped. Initiating cleanup...")

        pending_tasks = asyncio.all_tasks(loop=loop)
        pending_tasks = [task for task in pending_tasks if not task.cancelled() and not task.done()]

        logger.info(f"Found {len(pending_tasks)} pending asyncio tasks to cancel.")

        if pending_tasks:
            for task in pending_tasks:
                task.cancel()

            logger.info("Waiting for pending tasks to cancel...")
            try:
                loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
            except asyncio.CancelledError:
                logger.info("Pending tasks cancellation process completed.")
            except Exception as e:
                logger.error(f"Error during task cancellation waiting: {e}")
        else:
            logger.info("No pending asyncio tasks to cancel.")

        if not loop.is_closed():
            loop.close()
            logger.info("Asyncio event loop closed.")
        else:
            logger.info("Asyncio event loop was already closed.")

    logger.info("Application main thread finished.")
    sys.exit(0)