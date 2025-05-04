import asyncio
import websockets
import json
import logging
import uuid
import os
import socket
import time
from websockets.exceptions import ConnectionClosedError
from models.block import Block
from models.blockchain import Blockchain
from models.transaction import Transaction
from models.transaction_pool import TransactionPool
from core.config import BOOT_NODE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        self.processed_transactions = set()  # Track processed transaction IDs
        self.syncing_chain = False
        self.blocks_in_transit = set()
        self.tx_pool_syncing = False  # Track transaction pool sync state
        self.last_tx_pool_request = 0  # Timestamp of last MSG_REQUEST_TX_POOL
        self.tx_pool_request_cooldown = 5  # Seconds between requests

        # Message Types
        self.MSG_NEW_BLOCK = "NEW_BLOCK"
        self.MSG_NEW_TX = "NEW_TX"
        self.MSG_REQUEST_CHAIN = "REQUEST_CHAIN"
        self.MSG_RESPONSE_CHAIN = "RESPONSE_CHAIN"
        self.MSG_REGISTER_PEER = "REGISTER_PEER"
        self.MSG_PEER_LIST = "PEER_LIST"
        self.MSG_REQUEST_TX_POOL = "REQUEST_TX_POOL"
        self.MSG_RESPONSE_TX_POOL = "RESPONSE_TX_POOL"
        self.MSG_REQUEST_CHAIN_LENGTH = "REQUEST_CHAIN_LENGTH"
        self.MSG_RESPONSE_CHAIN_LENGTH = "RESPONSE_CHAIN_LENGTH"
        self.MSG_REQUEST_BLOCKS = "REQUEST_BLOCKS"
        self.MSG_RESPONSE_BLOCKS = "RESPONSE_BLOCKS"
        self.MSG_REQUEST_TX = "REQUEST_TX"
        self.MSG_RESPONSE_TX = "RESPONSE_TX"

    def create_message(self, msg_type, data):
        """Create a JSON formatted message."""
        return json.dumps({"type": msg_type, "data": data, "from": self.node_id})

    def save_peers(self):
        """Save the list of known peers to a file."""
        try:
            with open(self.peers_file, "w") as f:
                json.dump(list(self.known_peers), f)
        except Exception as e:
            logger.error(f"Error saving peers: {e}")

    def load_peers(self):
        """Load the list of known peers from a file."""
        try:
            if os.path.exists(self.peers_file):
                with open(self.peers_file, "r") as f:
                    peers = json.load(f)
                    return set(peers)
            return set()
        except Exception as e:
            logger.error(f"Error loading peers: {e}")
            return set()

    async def handle_message(self, message, websocket):
        """Handle incoming messages based on their type."""
        try:
            msg = json.loads(message)
            msg_type = msg['type']
            logger.info(f"Received message type: {msg_type}")
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
                    # Validate block transactions against UTXO set
                    for tx_json in block.data:
                        tx = Transaction.from_json(tx_json)
                        if not tx.is_coinbase:
                            input_data = tx.input
                            prev_tx_ids = input_data.get('prev_tx_ids', [])
                            input_address = input_data.get('address')
                            input_amount = input_data.get('amount', 0)
                            utxo_amount = 0
                            for prev_tx_id in prev_tx_ids:
                                if prev_tx_id not in self.blockchain.utxo_set or input_address not in self.blockchain.utxo_set[prev_tx_id]:
                                    # Request missing transaction
                                    await websocket.send(self.create_message(self.MSG_REQUEST_TX, prev_tx_id))
                                    logger.info(f"Requested missing transaction {prev_tx_id}")
                                    return
                                utxo_amount += self.blockchain.utxo_set[prev_tx_id].get(input_address, 0)
                            if input_amount > utxo_amount:
                                raise ValueError(f"Invalid transaction input: input amount {input_amount} exceeds UTXO amount {utxo_amount}")
                    self.blockchain.replace_chain(potential_chain)
                    self.transaction_pool.clear_blockchain_transactions(self.blockchain)
                    await self.broadcast(self.create_message(self.MSG_NEW_BLOCK, data), exclude=websocket)
                except Exception as e:
                    logger.error(f"Failed to replace chain: {e}")

            if msg_type == self.MSG_NEW_TX:
                transaction = Transaction.from_json(data)
                tx_id = transaction.id
                tx_time = transaction.input.get('timestamp', 0)
                logger.debug(f"Transaction ID: {tx_id}, Timestamp: {tx_time}")
                existing_tx = self.transaction_pool.transaction_map.get(tx_id)
                if existing_tx:
                    logger.debug(f"Existing transaction found: {existing_tx.input['timestamp']}")
                    if tx_time > existing_tx.input['timestamp']:
                        try:
                            Transaction.is_valid(transaction)
                            self.transaction_pool.set_transaction(transaction)
                            await self.broadcast(self.create_message(self.MSG_NEW_TX, data), exclude=websocket)
                            # Force tx pool sync to ensure all peers are updated
                            if time.time() - self.last_tx_pool_request > self.tx_pool_request_cooldown:
                                self.tx_pool_syncing = True
                                await self.broadcast(self.create_message(self.MSG_REQUEST_TX_POOL, None))
                                self.last_tx_pool_request = time.time()
                        except Exception as e:
                            logger.error(f"Failed to update transaction {tx_id}: {e}")
                elif tx_id not in self.processed_transactions:
                    try:
                        Transaction.is_valid(transaction)
                        self.transaction_pool.set_transaction(transaction)
                        self.processed_transactions.add(tx_id)
                        await self.broadcast(self.create_message(self.MSG_NEW_TX, data), exclude=websocket)
                        # Force tx pool sync to ensure all peers are updated
                        if time.time() - self.last_tx_pool_request > self.tx_pool_request_cooldown:
                            self.tx_pool_syncing = True
                            await self.broadcast(self.create_message(self.MSG_REQUEST_TX_POOL, None))
                            self.last_tx_pool_request = time.time()
                    except Exception as e:
                        logger.error(f"Failed to add transaction {tx_id}: {e}")
            elif msg_type == self.MSG_REQUEST_CHAIN:
                chain_data = [block.to_json() for block in self.blockchain.chain]
                await websocket.send(self.create_message(self.MSG_RESPONSE_CHAIN, chain_data))

            elif msg_type == self.MSG_RESPONSE_CHAIN:
                try:
                    received_chain = [Block.from_json(block_data) for block_data in data]
                    if len(received_chain) > len(self.blockchain.chain) and not self.syncing_chain:
                        logger.info(f"Received longer chain of length {len(received_chain)}")
                        self.syncing_chain = True
                        # Clear UTXO set and rebuild to avoid duplicates
                        self.blockchain.utxo_set.clear()
                        self.blockchain.replace_chain(received_chain)
                        self.transaction_pool.clear_blockchain_transactions(self.blockchain)
                        # Request tx pool to ensure sync after chain update
                        if not self.tx_pool_syncing and time.time() - self.last_tx_pool_request > self.tx_pool_request_cooldown:
                            self.tx_pool_syncing = True
                            await self.broadcast(self.create_message(self.MSG_REQUEST_TX_POOL, None))
                            self.last_tx_pool_request = time.time()
                    else:
                        logger.debug("Received chain not longer or syncing, ignoring")
                except Exception as e:
                    logger.error(f"Failed to replace chain with received chain: {e}")
                finally:
                    self.syncing_chain = False

            elif msg_type == self.MSG_REQUEST_TX_POOL:
                tx_pool_data = [tx.to_json() for tx in self.transaction_pool.transaction_map.values()]
                await websocket.send(self.create_message(self.MSG_RESPONSE_TX_POOL, tx_pool_data))

            elif msg_type == self.MSG_RESPONSE_TX_POOL:
                if not self.tx_pool_syncing:
                    logger.debug("Ignoring RESPONSE_TX_POOL as not syncing")
                    return
                added_count = 0
                for tx_data in data:
                    try:
                        transaction = Transaction.from_json(tx_data)
                        tx_id = transaction.id
                        tx_time = transaction.input.get('timestamp', 0)
                        existing_tx = self.transaction_pool.transaction_map.get(tx_id)
                        if existing_tx:
                            if tx_time > existing_tx.input['timestamp']:
                                Transaction.is_valid(transaction)
                                self.transaction_pool.set_transaction(transaction)
                                added_count += 1
                        elif tx_id not in self.processed_transactions:
                            Transaction.is_valid(transaction)
                            self.transaction_pool.set_transaction(transaction)
                            self.processed_transactions.add(tx_id)
                            added_count += 1
                    except Exception as e:
                        logger.error(f"Failed to add or update transaction from peer: {e}")
                logger.info(f"Successfully added or updated {added_count} transactions to pool from peer")
                # Continue syncing only if new transactions were added
                if added_count == 0:
                    self.tx_pool_syncing = False
                elif time.time() - self.last_tx_pool_request > self.tx_pool_request_cooldown:
                    await self.broadcast(self.create_message(self.MSG_REQUEST_TX_POOL, None))
                    self.last_tx_pool_request = time.time()

            elif msg_type == self.MSG_PEER_LIST:
                for peer_uri in data:
                    if peer_uri != self.node_id and peer_uri != self.my_uri and peer_uri not in self.peer_nodes and peer_uri not in self.known_peers:
                        self.known_peers.add(peer_uri)
                        self.save_peers()
                        asyncio.create_task(self.connect_to_peer(peer_uri))

            elif msg_type == self.MSG_REQUEST_CHAIN_LENGTH:
                await websocket.send(self.create_message(self.MSG_RESPONSE_CHAIN_LENGTH, len(self.blockchain.chain)))

            elif msg_type == self.MSG_RESPONSE_CHAIN_LENGTH:
                peer_length = data
                local_length = len(self.blockchain.chain)
                if peer_length > local_length and not self.syncing_chain:
                    await websocket.send(self.create_message(self.MSG_REQUEST_BLOCKS, local_length))
                    self.syncing_chain = True

            elif msg_type == self.MSG_REQUEST_BLOCKS:
                start_index = data
                blocks_to_send = self.blockchain.chain[start_index:]
                blocks_data = [block.to_json() for block in blocks_to_send]
                await websocket.send(self.create_message(self.MSG_RESPONSE_BLOCKS, blocks_data))

            elif msg_type == self.MSG_RESPONSE_BLOCKS:
                received_blocks_data = data
                if received_blocks_data:
                    received_blocks = [Block.from_json(block_data) for block_data in received_blocks_data]
                    potential_chain = self.blockchain.chain + received_blocks
                    try:
                        # Clear UTXO set and rebuild to avoid duplicates
                        self.blockchain.utxo_set.clear()
                        self.blockchain.replace_chain(potential_chain)
                        self.transaction_pool.clear_blockchain_transactions(self.blockchain)
                        # Request tx pool to ensure sync after chain update
                        if not self.tx_pool_syncing and time.time() - self.last_tx_pool_request > self.tx_pool_request_cooldown:
                            self.tx_pool_syncing = True
                            await self.broadcast(self.create_message(self.MSG_REQUEST_TX_POOL, None))
                            self.last_tx_pool_request = time.time()
                    except Exception as e:
                        logger.error(f"Error adding received blocks: {e}")
                    finally:
                        self.syncing_chain = False
                else:
                    self.syncing_chain = False

            elif msg_type == self.MSG_REQUEST_TX:
                tx_id = data
                tx = self.transaction_pool.transaction_map.get(tx_id)
                if tx:
                    await websocket.send(self.create_message(self.MSG_RESPONSE_TX, tx.to_json()))
                    logger.info(f"Sent transaction {tx_id} to peer")
                else:
                    logger.warning(f"Requested transaction {tx_id} not found in pool")

            elif msg_type == self.MSG_RESPONSE_TX:
                try:
                    transaction = Transaction.from_json(data)
                    tx_id = transaction.id
                    Transaction.is_valid(transaction)
                    self.transaction_pool.set_transaction(transaction)
                    self.processed_transactions.add(tx_id)
                    logger.info(f"Added transaction {tx_id} from peer")
                except Exception as e:
                    logger.error(f"Failed to process received transaction {data.get('id', 'unknown')}: {e}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON message received: {message}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def broadcast(self, message, exclude=None):
        """Broadcast a message to all connected peers."""
        logger.info(f"Broadcasting message to {len(self.peer_nodes)} peers: {list(self.peer_nodes.keys())}")
        failed_peers = []
        for uri, peer in list(self.peer_nodes.items()):
            if peer != exclude:
                try:
                    await peer.send(message)
                    logger.debug(f"Sent message to peer {uri}")
                except ConnectionClosedError:
                    logger.warning(f"Connection closed by peer {uri}, removing")
                    failed_peers.append(uri)
                except Exception as e:
                    logger.error(f"Failed to send message to {uri}: {e}, marking for retry")
                    failed_peers.append(uri)
        # Remove failed peers after iteration
        for uri in failed_peers:
            await self.remove_peer(uri)
        # If no peers were available, trigger a transaction pool sync
        if not self.peer_nodes and not self.tx_pool_syncing and time.time() - self.last_tx_pool_request > self.tx_pool_request_cooldown:
            self.tx_pool_syncing = True
            asyncio.create_task(self.broadcast(self.create_message(self.MSG_REQUEST_TX_POOL, None)))
            self.last_tx_pool_request = time.time()

    async def remove_peer(self, uri):
        """Remove a peer from the connected peers list."""
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
        """Handle new WebSocket connections."""
        try:
            peer_uri = f"ws://{websocket.remote_address[0]}:{websocket.remote_address[1]}"
            self.peer_nodes[peer_uri] = websocket
            logger.info(f"New peer connected: {peer_uri}")
            # Request chain length and tx pool on new connection
            await websocket.send(self.create_message(self.MSG_REQUEST_CHAIN_LENGTH, None))
            if not self.tx_pool_syncing and time.time() - self.last_tx_pool_request > self.tx_pool_request_cooldown:
                self.tx_pool_syncing = True
                await websocket.send(self.create_message(self.MSG_REQUEST_TX_POOL, None))
                self.last_tx_pool_request = time.time()
            async for message in websocket:
                await self.handle_message(message, websocket)
        except ConnectionClosedError:
            logger.warning(f"Peer disconnected: {peer_uri}")
            await self.remove_peer(peer_uri)
        except Exception as e:
            logger.error(f"Error in connection handler for {peer_uri}: {e}")
            await self.remove_peer(peer_uri)

    async def register_with_boot_node(self, uri, my_uri, retries=0):
        """Register with the boot node."""
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
        """Connect to a peer node."""
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
                await websocket.send(self.create_message(self.MSG_REQUEST_CHAIN_LENGTH, None))
                if not self.tx_pool_syncing and time.time() - self.last_tx_pool_request > self.tx_pool_request_cooldown:
                    self.tx_pool_syncing = True
                    await websocket.send(self.create_message(self.MSG_REQUEST_TX_POOL, None))
                    self.last_tx_pool_request = time.time()
            except Exception as e:
                logger.error(f"Failed to send requests to {uri}: {e}")
                await self.remove_peer(uri)
                return
            async for message in websocket:
                await self.handle_message(message, websocket)
        except ConnectionClosedError:
            logger.warning(f"Connection closed by peer {uri}")
            await self.remove_peer(uri)
            await asyncio.sleep(10)  # Increased delay to reduce rapid retries
            await self.connect_to_peer(uri, retries + 1)
        except Exception as e:
            logger.error(f"Failed to connect to {uri}: {e}, retry {retries + 1}/{self.max_retries}")
            await asyncio.sleep(10)  # Increased delay to reduce rapid retries
            await self.connect_to_peer(uri, retries + 1)

    async def start_server(self):
        """Start the WebSocket server."""
        self.server = await websockets.serve(self.connection_handler, "0.0.0.0", self.websocket_port)
        logger.info(f"WebSocket server started at port {self.websocket_port}")
        return self.server

    async def broadcast_transaction(self, transaction):
        """Broadcast a transaction to all peers."""
        message = self.create_message(self.MSG_NEW_TX, transaction.to_json())
        await self.broadcast(message)

    def broadcast_transaction_sync(self, transaction):
        """Broadcast a transaction to all peers synchronously."""
        if self.loop:
            future = asyncio.run_coroutine_threadsafe(self.broadcast_transaction(transaction), self.loop)
            future.result()
            logger.info(f"Broadcasted transaction {transaction.id}")
        else:
            logger.error("Event loop not available for broadcasting")
        

    async def broadcast_block(self, block):
        """Broadcast a block to all peers."""
        message = self.create_message(self.MSG_NEW_BLOCK, block.to_json())
        await self.broadcast(message)

    def broadcast_block_sync(self, block):
        """Broadcast a block to all peers synchronously."""
        if self.loop:
            future = asyncio.run_coroutine_threadsafe(self.broadcast_block(block), self.loop)
            future.result()
            logger.info(f"Broadcasted block {block.hash}")
        else:
            logger.error("Event loop not available for broadcasting")

    async def run_peer_discovery(self):
        """Run peer discovery logic."""
        logger.info("Starting peer discovery...")
        if self.my_uri != self.boot_node_uri:
            asyncio.create_task(self.register_with_boot_node(self.boot_node_uri, self.my_uri))
        known_peers = self.load_peers()
        for peer_uri in known_peers:
            if peer_uri != self.my_uri and peer_uri != self.node_id:
                asyncio.create_task(self.connect_to_peer(peer_uri))

    def start_websocket_server(self):
        """Start the WebSocket server and peer discovery."""
        async def run_node():
            await self.start_server()
            await self.run_peer_discovery()

        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(run_node())