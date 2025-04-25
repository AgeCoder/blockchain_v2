
import asyncio
import websockets
import json
import logging
import uuid
import os
import random
import socket
from websockets.exceptions import ConnectionClosedError
from backend.blockchain.block import Block
from backend.wallet.transaction import Transaction
from backend.config import BOOT_NODE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_public_ip():
    try:
        # Connect to an external server to get the public IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
    
class PubSub:
    def __init__(self, blockchain, transaction_pool):
        host = os.environ.get('HOST', get_public_ip())
        self.blockchain = blockchain
        self.transaction_pool = transaction_pool
        self.node_id = str(uuid.uuid4())
        self.peer_nodes = {}  # uri -> websocket
        self.known_peers = set()
        self.peers_file = "peers.json"
        self.boot_node_uri = BOOT_NODE
        self.max_retries = 3
        self.websocket_port = 5001 if os.environ.get('PEER') != 'True' else 6001
        self.my_uri = f"ws://{host}:{self.websocket_port}"
        self.server = None
        self.loop = None
        self.processed_transactions = set()  # Track processed transaction IDs only

        # Message Types
        self.MSG_NEW_BLOCK = "NEW_BLOCK"
        self.MSG_NEW_TX = "NEW_TX"
        self.MSG_REQUEST_CHAIN = "REQUEST_CHAIN"
        self.MSG_RESPONSE_CHAIN = "RESPONSE_CHAIN"
        self.MSG_REGISTER_PEER = "REGISTER_PEER"
        self.MSG_PEER_LIST = "PEER_LIST"
        self.MSG_REQUEST_TX_POOL = "REQUEST_TX_POOL"
        self.MSG_RESPONSE_TX_POOL = "RESPONSE_TX_POOL"

    def create_message(self, msg_type, data):
        return json.dumps({"type": msg_type, "data": data, "from": self.node_id})

    def save_peers(self):
        with open(self.peers_file, "w") as f:
            json.dump(list(self.known_peers), f)

    def load_peers(self):
        if os.path.exists(self.peers_file):
            with open(self.peers_file, "r") as f:
                peers = json.load(f)
                return set(peers)
        return set()

    async def handle_message(self, message, websocket):
        try:
            msg = json.loads(message)
            msg_type = msg['type']
            print(f"Received message type: {msg_type}")
            from_id = msg.get('from', 'unknown')
            logger.debug(f"Received message of type {msg_type} from {from_id}")
            data = msg['data']

            if msg_type == self.MSG_NEW_BLOCK:
                block = Block.from_json(data)
                last_block = self.blockchain.chain[-1]
                if block.hash == last_block.hash:
                    logger.info("Duplicate block received. Skipping.")
                    return
                potential_chain = self.blockchain.chain[:]
                potential_chain.append(block)
                try:
                    self.blockchain.replace_chain(potential_chain)
                    self.transaction_pool.clear_blockchain_transactions(self.blockchain)
                    logger.info("Blockchain replaced successfully!")
                    await self.broadcast(self.create_message(self.MSG_NEW_BLOCK, data), exclude=websocket)
                except Exception as e:
                    logger.error(f"Failed to replace chain: {e}")

            elif msg_type == self.MSG_NEW_TX:
                transaction = Transaction.from_json(data)
                tx_id = transaction.id
                tx_time = transaction.input.get('timestamp', None)
                print(f"Transaction ID: {tx_id}, Timestamp: {tx_time}")
                print(f"Processed transactions: {self.processed_transactions}")
                existing_tx = self.transaction_pool.transaction_map.get(tx_id)
                if existing_tx:
                    print(f"Existing transaction found: {existing_tx.input['timestamp']}")
                    # Update if the new transaction has a newer timestamp
                    if tx_time > existing_tx.input['timestamp']:
                        try:
                            Transaction.is_valid(transaction)
                            self.transaction_pool.set_transaction(transaction)
                            logger.info(f"Updated transaction {tx_id} with newer timestamp")
                            await self.broadcast(self.create_message(self.MSG_NEW_TX, data), exclude=websocket)
                        except Exception as e:
                            logger.error(f"Failed to update transaction {tx_id}: {e}")
                elif tx_id not in self.processed_transactions:
                    # Add new transaction
                    try:
                        Transaction.is_valid(transaction)
                        self.transaction_pool.set_transaction(transaction)
                        self.processed_transactions.add(tx_id)
                        logger.info(f"New transaction {tx_id} added to transaction pool")
                        await self.broadcast(self.create_message(self.MSG_NEW_TX, data), exclude=websocket)
                    except Exception as e:
                        logger.error(f"Failed to add transaction {tx_id}: {e}")

            elif msg_type == self.MSG_REQUEST_CHAIN:
                chain_data = [block.to_json() for block in self.blockchain.chain]
                await websocket.send(self.create_message(self.MSG_RESPONSE_CHAIN, chain_data))
                logger.info("Sent blockchain response")

            elif msg_type == self.MSG_RESPONSE_CHAIN:
                try:
                    received_chain = [Block.from_json(block_data) for block_data in data]
                    self.blockchain.replace_chain(received_chain)
                    self.transaction_pool.clear_blockchain_transactions(self.blockchain)
                    logger.info(f"Blockchain replaced with received chain: {len(received_chain)} blocks")
                except Exception as e:
                    logger.error(f"Failed to replace chain with received chain: {e}")

            elif msg_type == self.MSG_REQUEST_TX_POOL:
                logger.info("Received request for transaction pool")
                tx_pool_data = [tx.to_json() for tx in self.transaction_pool.transaction_map.values()]
                await websocket.send(self.create_message(self.MSG_RESPONSE_TX_POOL, tx_pool_data))
                logger.info("Sent transaction pool response")

            elif msg_type == self.MSG_RESPONSE_TX_POOL:
                logger.info(f"Received transaction pool with {len(data)} transactions")
                added_count = 0
                for tx_data in data:
                    try:
                        transaction = Transaction.from_json(tx_data)
                        tx_id = transaction.id
                        tx_time = transaction.input.get('timestamp', None)
                        existing_tx = self.transaction_pool.transaction_map.get(tx_id)
                        if existing_tx:
                            # Update if the new transaction has a newer timestamp
                            if tx_time > existing_tx.input['timestamp']:
                                Transaction.is_valid(transaction)
                                self.transaction_pool.set_transaction(transaction)
                                logger.debug(f"Updated transaction {tx_id} with newer timestamp")
                                added_count += 1
                        elif tx_id not in self.processed_transactions:
                            # Add new transaction
                            Transaction.is_valid(transaction)
                            self.transaction_pool.set_transaction(transaction)
                            self.processed_transactions.add(tx_id)
                            logger.debug(f"Added new transaction {tx_id} from peer to pool")
                            added_count += 1
                    except Exception as e:
                        logger.error(f"Failed to add or update transaction from peer: {e}")
                logger.info(f"Successfully added or updated {added_count} transactions to pool")

            elif msg_type == self.MSG_PEER_LIST:
                logger.info(f"Received peer list: {data}")
                for peer_uri in data:
                    if peer_uri != self.node_id and peer_uri != self.my_uri and peer_uri not in self.peer_nodes:
                        self.known_peers.add(peer_uri)
                        self.save_peers()
                        asyncio.create_task(self.connect_to_peer(peer_uri))

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def broadcast(self, message, exclude=None):
        logger.info(f"Broadcasting message to {len(self.peer_nodes)} peers: {list(self.peer_nodes.keys())}")
        for uri, peer in list(self.peer_nodes.items()):
            if peer != exclude:
                try:
                    await peer.send(message)
                    logger.debug(f"Sent message to peer {uri}")
                except Exception as e:
                    logger.warning(f"Removing peer {uri}, reason: {e}")
                    await self.remove_peer(uri)

    async def remove_peer(self, uri):
        if uri in self.peer_nodes:
            try:
                await self.peer_nodes[uri].close()
            except:
                pass
            del self.peer_nodes[uri]
            self.known_peers.discard(uri)
            self.save_peers()
            logger.info(f"Peer {uri} removed from known peers")

    async def connection_handler(self, websocket):
        try:
            peer_uri = f"ws://{websocket.remote_address[0]}:{websocket.remote_address[1]}"  # Track incoming peer URI
            self.peer_nodes[peer_uri] = websocket
            logger.info(f"New peer connected: {peer_uri}")
            async for message in websocket:
                await self.handle_message(message, websocket)
        except ConnectionClosedError:
            logger.warning(f"Peer {peer_uri} disconnected")
            await self.remove_peer(peer_uri)

    async def register_with_boot_node(self, uri, my_uri, retries=0):
        if retries >= self.max_retries:
            logger.error(f"Max retries reached for boot node {uri}")
            return
        try:
            websocket = await websockets.connect(uri)
            await websocket.send(self.create_message(self.MSG_REGISTER_PEER, my_uri))
            async for message in websocket:
                await self.handle_message(message, websocket)
        except Exception as e:
            logger.error(f"Failed to register with boot node: {e}, retry {retries + 1}/{self.max_retries}")
            await asyncio.sleep(5)
            await self.register_with_boot_node(uri, my_uri, retries + 1)

    async def connect_to_peer(self, uri, retries=0):
        if uri in self.peer_nodes or retries >= self.max_retries:
            if retries >= self.max_retries:
                logger.info(f"Max retries reached for peer {uri}, removing from known peers")
                self.known_peers.discard(uri)
                self.save_peers()
            return
        try:
            websocket = await websockets.connect(uri)
            self.peer_nodes[uri] = websocket
            logger.info(f"Connected to peer {uri}")
            try:
                await websocket.send(self.create_message(self.MSG_REQUEST_CHAIN, None))
                logger.info(f"Sent MSG_REQUEST_CHAIN to {uri}")
                await websocket.send(self.create_message(self.MSG_REQUEST_TX_POOL, None))
                logger.info(f"Sent MSG_REQUEST_TX_POOL to {uri}")
            except Exception as e:
                logger.error(f"Failed to send requests to {uri}: {e}")
                await self.remove_peer(uri)
                return
            async for message in websocket:
                await self.handle_message(message, websocket)
        except ConnectionClosedError:
            logger.warning(f"Connection closed by peer {uri}")
            await self.remove_peer(uri)
            await asyncio.sleep(5)
            await self.connect_to_peer(uri, retries + 1)
        except Exception as e:
            logger.error(f"Failed to connect to {uri}: {e}, retry {retries + 1}/{self.max_retries}")
            await asyncio.sleep(5)
            await self.connect_to_peer(uri, retries + 1)

    async def start_server(self):
        self.server = await websockets.serve(self.connection_handler, "0.0.0.0", self.websocket_port)
        logger.info(f"WebSocket server started at port {self.websocket_port}")
        return self.server

    async def broadcast_transaction(self, transaction):
        message = self.create_message(self.MSG_NEW_TX, transaction.to_json())
        await self.broadcast(message)

    def broadcast_transaction_sync(self, transaction):
        tx_id = transaction.id
        tx_time = transaction.input.get('timestamp', None)
        print(f"Transaction ID: {tx_id}, Timestamp: {tx_time}")
        existing_tx = self.transaction_pool.transaction_map.get(tx_id)
        if existing_tx:
            if tx_time > existing_tx.input['timestamp']:
                try:
                    Transaction.is_valid(transaction)
                    self.transaction_pool.set_transaction(transaction)
                    logger.info(f"Updated transaction {tx_id} locally")
                    if self.loop:
                        future = asyncio.run_coroutine_threadsafe(self.broadcast_transaction(transaction), self.loop)
                        future.result()
                        logger.info(f"Broadcasted updated transaction {tx_id} to peers")
                    else:
                        logger.error("Event loop not available for broadcasting")
                except Exception as e:
                    logger.error(f"Failed to update transaction {tx_id}: {e}")
        elif tx_id not in self.processed_transactions:
            try:
                Transaction.is_valid(transaction)
                self.transaction_pool.set_transaction(transaction)
                self.processed_transactions.add(tx_id)
                logger.info(f"New transaction {tx_id} added to transaction pool")
                if self.loop:
                    print(f"Broadcasting new transaction {tx_id} to peers")
                    future = asyncio.run_coroutine_threadsafe(self.broadcast_transaction(transaction), self.loop)
                    future.result()
                    logger.info(f"Broadcasted new transaction {tx_id} to peers")
                else:
                    logger.error("Event loop not available for broadcasting")
            except Exception as e:
                logger.error(f"Failed to broadcast transaction {tx_id}: {e}")

    async def broadcast_block(self, block):
        message = self.create_message(self.MSG_NEW_BLOCK, block.to_json())
        await self.broadcast(message)

    def broadcast_block_sync(self, block):
        if self.loop:
            future = asyncio.run_coroutine_threadsafe(self.broadcast_block(block), self.loop)
            future.result()
        else:
            logger.error("Event loop not available for broadcasting")

    async def run_peer_discovery(self):
        logger.info("Starting peer discovery...")
        if self.my_uri != self.boot_node_uri:
            logger.info(f"Attempting to register with boot node at {self.boot_node_uri}")
            asyncio.create_task(self.register_with_boot_node(self.boot_node_uri, self.my_uri))
        known_peers = self.load_peers()
        logger.info(f"Loaded {len(known_peers)} known peers: {known_peers}")
        for peer_uri in known_peers:
            if peer_uri != self.my_uri and peer_uri != self.node_id:
                logger.info(f"Attempting to connect to known peer: {peer_uri}")
                asyncio.create_task(self.connect_to_peer(peer_uri))

    def start_websocket_server(self):
        async def run_node():
            await self.start_server()
            await self.run_peer_discovery()

        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(run_node())