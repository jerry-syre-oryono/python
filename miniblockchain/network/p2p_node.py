import socket
import threading
import json
import time
import pickle
from typing import Dict, List, Set, Tuple
from queue import Queue
import select

from miniblockchain.core.blockchain import Blockchain
from miniblockchain.core.block import Block
from miniblockchain.core.transaction import Transaction

class P2PNode:
    """Full P2P node with socket-based networking."""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 6000):
        self.host = host
        self.port = port
        self.address = f"{host}:{port}"
        
        self.blockchain = Blockchain()
        self.peers: Set[str] = set()
        self.peer_sockets: Dict[str, socket.socket] = {}
        
        # Message queues
        self.message_queue = Queue()
        self.broadcast_queue = Queue()
        
        # Server socket
        self.server_socket = None
        self.running = False
        
        # Threads
        self.server_thread = None
        self.message_handler_thread = None
        self.broadcast_thread = None
        
        # Known peer discovery (simplified)
        self.bootstrap_nodes = [
            '127.0.0.1:6001',
            '127.0.0.1:6002'
        ]
    
    def start(self):
        """Start the P2P node."""
        self.running = True
        
        # Create server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1.0)
        
        print(f"P2P Node started at {self.address}")
        
        # Connect to bootstrap nodes
        self.connect_to_bootstrap_nodes()
        
        # Start threads
        self.server_thread = threading.Thread(target=self.accept_connections)
        self.message_handler_thread = threading.Thread(target=self.handle_messages)
        self.broadcast_thread = threading.Thread(target=self.broadcast_messages)
        
        self.server_thread.start()
        self.message_handler_thread.start()
        self.broadcast_thread.start()
        
        # Send version message to peers
        self.broadcast_version()
    
    def connect_to_bootstrap_nodes(self):
        """Connect to bootstrap nodes."""
        for node_address in self.bootstrap_nodes:
            if node_address != self.address:
                try:
                    self.connect_to_node(node_address)
                except:
                    print(f"Failed to connect to bootstrap node {node_address}")
    
    def connect_to_node(self, node_address: str):
        """Connect to a specific node."""
        if node_address in self.peers or node_address == self.address:
            return
        
        host, port = node_address.split(':')
        port = int(port)
        
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((host, port))
            
            # Send version message
            version_msg = self.create_message("version", {
                "version": 1,
                "address": self.address,
                "height": len(self.blockchain.chain)
            })
            self.send_to_socket(peer_socket, version_msg)
            
            # Add to peers
            self.peers.add(node_address)
            self.peer_sockets[node_address] = peer_socket
            
            print(f"Connected to node: {node_address}")
            
        except Exception as e:
            print(f"Failed to connect to {node_address}: {e}")
    
    def accept_connections(self):
        """Accept incoming connections."""
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_socket.settimeout(10.0)
                
                # Handle connection in new thread
                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                thread.daemon = True
                thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")
    
    def handle_client(self, client_socket: socket.socket, client_address: Tuple[str, int]):
        """Handle a client connection."""
        node_address = f"{client_address[0]}:{client_address[1]}"
        
        try:
            # Receive version message
            data = self.receive_from_socket(client_socket)
            if not data:
                return
            
            message = pickle.loads(data)
            
            if message["type"] == "version":
                self.peers.add(node_address)
                self.peer_sockets[node_address] = client_socket
                
                # Send version back
                version_msg = self.create_message("version", {
                    "version": 1,
                    "address": self.address,
                    "height": len(self.blockchain.chain)
                })
                self.send_to_socket(client_socket, version_msg)
                
                # Send addr message with our peers
                addr_msg = self.create_message("addr", {
                    "peers": list(self.peers)
                })
                self.send_to_socket(client_socket, addr_msg)
                
                print(f"New connection from {node_address}")
            
            # Handle further messages from this client
            while self.running:
                data = self.receive_from_socket(client_socket)
                if not data:
                    break
                
                message = pickle.loads(data)
                self.message_queue.put((node_address, message))
        
        except Exception as e:
            print(f"Error handling client {node_address}: {e}")
        finally:
            if node_address in self.peers:
                self.peers.remove(node_address)
                if node_address in self.peer_sockets:
                    del self.peer_sockets[node_address]
            client_socket.close()
    
    def handle_messages(self):
        """Process messages from the queue."""
        while self.running:
            try:
                node_address, message = self.message_queue.get(timeout=1.0)
                self.process_message(node_address, message)
            except:
                continue
    
    def process_message(self, node_address: str, message: Dict):
        """Process a received message."""
        msg_type = message["type"]
        payload = message["payload"]
        
        if msg_type == "version":
            # Already handled during connection
            pass
        
        elif msg_type == "addr":
            # New peers discovered
            new_peers = payload.get("peers", [])
            for peer in new_peers:
                if peer not in self.peers and peer != self.address:
                    threading.Thread(target=self.connect_to_node, args=(peer,)).start()
        
        elif msg_type == "inv":
            # Inventory announcement (blocks or transactions)
            inv_type = payload["type"]  # "block" or "tx"
            items = payload["items"]  # List of hashes
            
            # Request items we don't have
            if inv_type == "block":
                for block_hash in items:
                    if not self.has_block(block_hash):
                        self.request_block(node_address, block_hash)
            elif inv_type == "tx":
                for tx_id in items:
                    if tx_id not in self.blockchain.mempool:
                        self.request_transaction(node_address, tx_id)
        
        elif msg_type == "getdata":
            # Peer requests data from us
            data_type = payload["type"]
            item_hash = payload["hash"]
            
            if data_type == "block":
                block = self.get_block_by_hash(item_hash)
                if block:
                    self.send_block(node_address, block)
            elif data_type == "tx":
                tx = self.get_transaction_by_hash(item_hash)
                if tx:
                    self.send_transaction(node_address, tx)
        
        elif msg_type == "block":
            # Received a block
            block_data = payload["block"]
            block = Block.from_dict(block_data)
            
            # Validate and add to blockchain
            if self.validate_and_add_block(block):
                # Broadcast to other peers
                self.broadcast_inv("block", [block.hash])
                print(f"New block received and added: #{block.index}")
        
        elif msg_type == "tx":
            # Received a transaction
            tx_data = payload["transaction"]
            # Convert to Transaction object (simplified)
            success, msg = self.blockchain.add_transaction(tx_data)
            if success:
                # Broadcast to other peers
                self.broadcast_inv("tx", [tx_data["tx_id"]])
                print(f"New transaction received: {tx_data['tx_id'][:16]}...")
        
        elif msg_type == "getblocks":
            # Peer wants our blocks
            start_height = payload.get("start_height", 0)
            block_hashes = []
            
            for i in range(start_height, len(self.blockchain.chain)):
                if i < len(self.blockchain.chain):
                    block_hashes.append(self.blockchain.chain[i].hash)
            
            inv_msg = self.create_message("inv", {
                "type": "block",
                "items": block_hashes[-10:]  # Send last 10
            })
            self.send_to_node(node_address, inv_msg)
    
    def validate_and_add_block(self, block: Block) -> bool:
        """Validate a block and add to blockchain."""
        # Simplified validation
        if block.index == len(self.blockchain.chain):
            if block.previous_hash == self.blockchain.get_last_block().hash:
                if block.hash.startswith('0' * self.blockchain.difficulty):
                    self.blockchain.chain.append(block)
                    return True
        return False
    
    def broadcast_messages(self):
        """Broadcast messages from the queue."""
        while self.running:
            try:
                message = self.broadcast_queue.get(timeout=1.0)
                self.broadcast_to_all(message)
            except:
                continue
    
    def broadcast_to_all(self, message: Dict):
        """Broadcast a message to all peers."""
        data = pickle.dumps(message)
        
        dead_peers = []
        for node_address, peer_socket in self.peer_sockets.items():
            try:
                peer_socket.sendall(len(data).to_bytes(4, 'big') + data)
            except:
                dead_peers.append(node_address)
        
        # Remove dead peers
        for node_address in dead_peers:
            if node_address in self.peers:
                self.peers.remove(node_address)
            if node_address in self.peer_sockets:
                self.peer_sockets[node_address].close()
                del self.peer_sockets[node_address]
    
    def broadcast_version(self):
        """Broadcast version message."""
        version_msg = self.create_message("version", {
            "version": 1,
            "address": self.address,
            "height": len(self.blockchain.chain)
        })
        self.broadcast_queue.put(version_msg)
    
    def broadcast_inv(self, inv_type: str, items: List[str]):
        """Broadcast inventory announcement."""
        inv_msg = self.create_message("inv", {
            "type": inv_type,
            "items": items
        })
        self.broadcast_queue.put(inv_msg)
    
    def broadcast_transaction(self, tx: Transaction):
        """Broadcast a transaction."""
        tx_msg = self.create_message("tx", {
            "transaction": tx.to_dict()
        })
        self.broadcast_queue.put(tx_msg)
    
    def broadcast_block(self, block: Block):
        """Broadcast a block."""
        block_msg = self.create_message("block", {
            "block": block.to_dict()
        })
        self.broadcast_queue.put(block_msg)
    
    def send_to_node(self, node_address: str, message: Dict):
        """Send message to specific node."""
        if node_address in self.peer_sockets:
            data = pickle.dumps(message)
            self.send_to_socket(self.peer_sockets[node_address], data)
    
    def send_to_socket(self, sock: socket.socket, data: bytes):
        """Send data to socket with length prefix."""
        try:
            sock.sendall(len(data).to_bytes(4, 'big') + data)
        except:
            pass
    
    def receive_from_socket(self, sock: socket.socket) -> bytes:
        """Receive data from socket with length prefix."""
        try:
            length_bytes = sock.recv(4)
            if not length_bytes:
                return None
            
            length = int.from_bytes(length_bytes, 'big')
            data = b""
            
            while len(data) < length:
                chunk = sock.recv(min(4096, length - len(data)))
                if not chunk:
                    return None
                data += chunk
            
            return data
        except:
            return None
    
    def create_message(self, msg_type: str, payload: Dict) -> Dict:
        """Create a message dictionary."""
        return {
            "type": msg_type,
            "payload": payload,
            "timestamp": time.time()
        }
    
    def has_block(self, block_hash: str) -> bool:
        """Check if we have a block."""
        for block in self.blockchain.chain:
            if block.hash == block_hash:
                return True
        return False
    
    def get_block_by_hash(self, block_hash: str) -> Block:
        """Get block by hash."""
        for block in self.blockchain.chain:
            if block.hash == block_hash:
                return block
        return None
    
    def get_transaction_by_hash(self, tx_hash: str) -> Transaction:
        """Get transaction by hash."""
        # Search in blockchain
        for block in self.blockchain.chain:
            for tx_data in block.transactions:
                if tx_data.get("tx_id") == tx_hash:
                    # Convert back to Transaction
                    return Transaction.from_dict(tx_data)
        
        # Search in mempool
        return self.blockchain.mempool.get(tx_hash)
    
    def request_block(self, node_address: str, block_hash: str):
        """Request a block from a peer."""
        getdata_msg = self.create_message("getdata", {
            "type": "block",
            "hash": block_hash
        })
        self.send_to_node(node_address, getdata_msg)
    
    def request_transaction(self, node_address: str, tx_hash: str):
        """Request a transaction from a peer."""
        getdata_msg = self.create_message("getdata", {
            "type": "tx",
            "hash": tx_hash
        })
        self.send_to_node(node_address, getdata_msg)
    
    def stop(self):
        """Stop the P2P node."""
        self.running = False
        
        # Close all sockets
        if self.server_socket:
            self.server_socket.close()
        
        for peer_socket in self.peer_sockets.values():
            peer_socket.close()
        
        print("P2P Node stopped")