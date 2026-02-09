import requests
import threading
import time
from miniblockchain.core.blockchain import Blockchain
import json

class P2PNetwork:
    def __init__(self):
        self.nodes = set()  # Other nodes in network
        self.blockchain = Blockchain()
    
    def register_node(self, address: str):
        """Add a new node to the network."""
        self.nodes.add(address)
        print(f"Node registered: {address}")
    
    def broadcast_transaction(self, transaction: Dict):
        """Send transaction to all nodes."""
        for node in self.nodes:
            try:
                requests.post(f"http://{node}/transaction", 
                            json=transaction, 
                            timeout=2)
            except:
                print(f"Failed to broadcast to {node}")
    
    def broadcast_block(self, block):
        """Send mined block to all nodes."""
        for node in self.nodes:
            try:
                block_dict = {
                    "index": block.index,
                    "transactions": block.transactions,
                    "timestamp": block.timestamp,
                    "previous_hash": block.previous_hash,
                    "nonce": block.nonce,
                    "hash": block.hash
                }
                requests.post(f"http://{node}/block", 
                            json=block_dict, 
                            timeout=2)
            except:
                print(f"Failed to broadcast block to {node}")
    
    def resolve_conflicts(self) -> bool:
        """
        Consensus algorithm: Replace our chain with longest valid chain in network.
        This demonstrates how blockchains achieve consensus.
        """
        longest_chain = None
        max_length = len(self.blockchain.chain)
        
        # Get chains from all nodes
        for node in self.nodes:
            try:
                response = requests.get(f"http://{node}/chain", timeout=3)
                if response.status_code == 200:
                    chain_data = response.json()
                    chain_length = chain_data["length"]
                    chain = chain_data["chain"]
                    
                    # Check if longer and valid
                    if chain_length > max_length:
                        # Create temporary blockchain to validate
                        temp_blockchain = Blockchain()
                        temp_blockchain.chain = []
                        
                        for block_data in chain:
                            block = Block(
                                index=block_data["index"],
                                transactions=block_data["transactions"],
                                timestamp=block_data["timestamp"],
                                previous_hash=block_data["previous_hash"],
                                nonce=block_data["nonce"]
                            )
                            block.hash = block_data["hash"]
                            temp_blockchain.chain.append(block)
                        
                        if temp_blockchain.is_chain_valid():
                            max_length = chain_length
                            longest_chain = temp_blockchain.chain
            except:
                continue
        
        # Replace our chain if we found a longer valid one
        if longest_chain:
            self.blockchain.chain = longest_chain
            return True
        
        return False