# main.py
import asyncio
import threading
import signal
import sys
import os
import logging
import socket
from fastapi import FastAPI
from uvicorn import Config, Server
from fastapi.middleware.cors import CORSMiddleware
from dependencies import app, get_blockchain, get_transaction_pool, get_pubsub
from core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import routers after app creation
from routers import blockchain, transaction, wallet, general

# Include routers
app.include_router(blockchain.router)
app.include_router(transaction.router)
app.include_router(wallet.router)
app.include_router(general.router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def get_public_ip():
    """Get the public IP address of the current machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
async def run_fastapi_server(app: FastAPI, port: int):
    """Run the FastAPI server using Uvicorn."""
    try:
        config = Config(app=app, host="0.0.0.0", port=port, log_level="info")
        server = Server(config)
        logger.info(f"Starting FastAPI server on port {port}...")
        await server.serve()
    except Exception as e:
        logger.error(f"Error starting FastAPI server: {e}")

def handle_shutdown(sig, frame):
    """Handle shutdown signals (SIGINT, SIGTERM) for graceful shutdown."""
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
    # Set environment variables
    os.environ['HOST'] = os.environ.get('HOST', get_public_ip())
    is_peer = settings.peer
    port = settings.root_port if not is_peer else 4000

    # Configure signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Initialize blockchain, transaction pool, and pubsub
    blockchain = get_blockchain()
    transaction_pool = get_transaction_pool()
    pubsub = get_pubsub()

    # Set up asyncio event loop
    try:
        loop = asyncio.get_running_loop()
        logger.info("Using existing asyncio event loop.")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("Created and set a new asyncio event loop.")

    pubsub.loop = loop
    logger.info(f"PubSub instance configured with asyncio loop: {pubsub.loop}")

    # Start FastAPI server in a separate thread
    logger.info(f"Starting FastAPI server in a separate thread on port {port}...")
    fastapi_thread = threading.Thread(
        target=lambda: asyncio.run(run_fastapi_server(app, port)),
        daemon=True
    )
    fastapi_thread.start()
    logger.info("FastAPI thread started.")

    # Start WebSocket server and peer discovery tasks
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

        # Cancel pending tasks
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

        # Close the event loop
        if not loop.is_closed():
            loop.close()
            logger.info("Asyncio event loop closed.")
        else:
            logger.info("Asyncio event loop was already closed.")

    logger.info("Application main thread finished.")
    sys.exit(0)