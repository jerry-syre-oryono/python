import hashlib
import json
import time
from typing import List, Dict, Any

class Block:
    def __init__(self, index: int, transactions: List[Dict], timestamp: float, previous_hash: str, nonce: int = 0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()
    
    def compute_hash(self) -> str:
        """
        Create a SHA-256 hash of the block's contents.
        This demonstrates cryptographic hashing - the core of blockchain integrity.
        """
        block_string = json.dumps({
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        
        # SHA-256: Bitcoin's hash function. 256 bits = 64 hex characters.
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def __repr__(self) -> str:
        return f"Block(Index: {self.index}, Hash: {self.hash[:10]}..., Previous: {self.previous_hash[:10]}...)"


class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict] = []
        self.create_genesis_block()

    def create_genesis_block(self):
        """
        Creates the first block in the blockchain.
        """
        genesis_block = Block(
            index=0,
            transactions=[],
            timestamp=time.time(),
            previous_hash="0",
            nonce=0
        )
        self.chain.append(genesis_block)

    def get_last_block(self) -> Block:
        """
        Returns the last block in the chain.
        """
        return self.chain[-1]

    def add_transaction(self, transaction: Dict) -> int:
        """
        Add a new transaction to pending list.
        In real blockchain, we'd verify signature here.
        """
        # Basic validation
        if not all(k in transaction for k in ["from", "to", "amount"]):
            raise ValueError("Transaction must include 'from', 'to', and 'amount'")
        
        if transaction["amount"] <= 0:
            raise ValueError("Transaction amount must be positive")
        
        self.pending_transactions.append(transaction)
        return self.get_last_block().index + 1  # Will be included in next block
    
    def get_balance(self, address: str) -> float:
        """Calculate balance for an address by scanning all blocks."""
        balance = 0.0
        
        for block in self.chain:
            for tx in block.transactions:
                if tx["to"] == address:
                    balance += tx["amount"]
                if tx["from"] == address:
                    balance -= tx["amount"]
        
        return balance