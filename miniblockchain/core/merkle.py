import hashlib
from typing import List, Tuple, Optional

class MerkleTree:
    """
    Merkle Tree implementation for efficient transaction verification.
    Each leaf is a transaction hash, internal nodes are hashes of children.
    """
    
    def __init__(self, transactions: List[str]):
        """
        Initialize with transaction hashes.
        :param transactions: List of SHA-256 hashed transaction data
        """
        if not transactions:
            self.root = ""
            self.levels = []
            return
            
        # Ensure even number of leaves by duplicating last if odd
        self.leaves = transactions.copy()
        if len(self.leaves) % 2 != 0:
            self.leaves.append(self.leaves[-1])
        
        self.levels = self.build_tree(self.leaves)
        self.root = self.levels[-1][0] if self.levels else ""
    
    @staticmethod
    def hash_pair(left: str, right: str) -> str:
        """Hash two nodes together."""
        combined = left + right
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def build_tree(self, leaves: List[str]) -> List[List[str]]:
        """Build the Merkle Tree from leaves to root."""
        levels = [leaves]
        
        while len(levels[-1]) > 1:
            current_level = levels[-1]
            next_level = []
            
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i+1] if i+1 < len(current_level) else current_level[i]
                next_level.append(self.hash_pair(left, right))
            
            levels.append(next_level)
        
        return levels
    
    def get_root(self) -> str:
        """Return the Merkle root hash."""
        return self.root
    
    def get_proof(self, index: int) -> List[Tuple[str, bool]]:
        """
        Get Merkle proof for a leaf at given index.
        Returns list of (hash, is_left) pairs needed to verify.
        :param index: Index of leaf to prove
        :return: Proof as list of (sibling_hash, position) tuples
        """
        if index >= len(self.leaves):
            raise IndexError("Leaf index out of bounds")
        
        proof = []
        current_index = index
        
        for level in self.levels[:-1]:  # Don't include root level
            is_left = current_index % 2 == 0
            sibling_index = current_index + 1 if is_left else current_index - 1
            
            if sibling_index < len(level):
                proof.append((level[sibling_index], not is_left))
            
            current_index //= 2
        
        return proof
    
    @staticmethod
    def verify_proof(leaf_hash: str, proof: List[Tuple[str, bool]], root_hash: str) -> bool:
        """
        Verify a Merkle proof.
        :param leaf_hash: Hash of leaf to verify
        :param proof: List of (sibling_hash, is_left) tuples
        :param root_hash: Expected Merkle root
        :return: True if proof is valid
        """
        current_hash = leaf_hash
        
        for sibling_hash, is_left in proof:
            if is_left:
                # Current is left, sibling is right
                current_hash = MerkleTree.hash_pair(current_hash, sibling_hash)
            else:
                # Current is right, sibling is left
                current_hash = MerkleTree.hash_pair(sibling_hash, current_hash)
        
        return current_hash == root_hash
    
    def visualize(self) -> str:
        """Return string visualization of the tree."""
        lines = []
        for i, level in enumerate(self.levels):
            lines.append(f"Level {i}: {[h[:8] + '...' for h in level]}")
        return "\n".join(lines)


def hash_transaction(tx_data: dict) -> str:
    """Helper to hash transaction data."""
    import json
    tx_string = json.dumps(tx_data, sort_keys=True)
    return hashlib.sha256(tx_string.encode()).hexdigest()