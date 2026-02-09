import hashlib
import json
import time
from typing import List, Dict, Any
from .merkle import MerkleTree, hash_transaction

class Block:
    def __init__(self, index: int, transactions: List[Dict], timestamp: float, 
                 previous_hash: str, nonce: int = 0, merkle_root: str = None):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce
        
        # Calculate Merkle root if not provided
        if merkle_root is None:
            tx_hashes = [hash_transaction(tx) for tx in transactions]
            merkle_tree = MerkleTree(tx_hashes)
            self.merkle_root = merkle_tree.root
            self.merkle_tree = merkle_tree
        else:
            self.merkle_root = merkle_root
            tx_hashes = [hash_transaction(tx) for tx in transactions]
            self.merkle_tree = MerkleTree(tx_hashes)
        
        self.hash = self.compute_hash()
    
    def compute_hash(self) -> str:
        """Include Merkle root in block hash calculation."""
        block_string = json.dumps({
            "index": self.index,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def verify_transaction_inclusion(self, tx_data: dict) -> Tuple[bool, List]:
        """
        Verify if a transaction is included in this block.
        Returns (is_included, proof)
        """
        tx_hash = hash_transaction(tx_data)
        
        # Find transaction index
        tx_hashes = [hash_transaction(tx) for tx in self.transactions]
        try:
            tx_index = tx_hashes.index(tx_hash)
        except ValueError:
            return False, []
        
        # Get Merkle proof
        proof = self.merkle_tree.get_proof(tx_index)
        
        # Verify proof
        is_valid = MerkleTree.verify_proof(tx_hash, proof, self.merkle_root)
        
        return is_valid, proof
    
    def to_dict(self) -> Dict:
        """Convert block to dictionary for serialization."""
        return {
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
            "merkle_root": self.merkle_root
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Block':
        """Create block from dictionary."""
        block = cls(
            index=data["index"],
            transactions=data["transactions"],
            timestamp=data["timestamp"],
            previous_hash=data["previous_hash"],
            nonce=data["nonce"],
            merkle_root=data.get("merkle_root")
        )
        block.hash = data["hash"]  # Set hash directly since it was computed
        return block