import hashlib
import json
import time
from typing import List, Dict, Tuple, Set
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa.util import sigencode_der, sigdecode_der
from .merkle import hash_transaction

class UTXO:
    """Unspent Transaction Output - represents a "coin"."""
    
    def __init__(self, tx_id: str, output_index: int, amount: float, 
                 recipient_address: str, is_coinbase: bool = False):
        self.tx_id = tx_id  # Transaction that created this UTXO
        self.output_index = output_index  # Which output in that transaction
        self.amount = amount
        self.recipient_address = recipient_address
        self.is_coinbase = is_coinbase  # Coinbase UTXOs have special rules
    
    def to_dict(self) -> Dict:
        return {
            "tx_id": self.tx_id,
            "output_index": self.output_index,
            "amount": self.amount,
            "recipient": self.recipient_address,
            "is_coinbase": self.is_coinbase
        }
    
    def __repr__(self):
        return f"UTXO({self.tx_id[:8]}...:{self.output_index}, {self.amount} -> {self.recipient_address[:8]}...)"


class TxInput:
    """Transaction Input - references a UTXO to be spent."""
    
    def __init__(self, tx_id: str, output_index: int, signature: str = None, 
                 public_key: str = None):
        self.tx_id = tx_id
        self.output_index = output_index
        self.signature = signature
        self.public_key = public_key
    
    def to_dict(self) -> Dict:
        return {
            "tx_id": self.tx_id,
            "output_index": self.output_index,
            "signature": self.signature,
            "public_key": self.public_key
        }


class TxOutput:
    """Transaction Output - creates new UTXOs."""
    
    def __init__(self, amount: float, recipient_address: str):
        self.amount = amount
        self.recipient_address = recipient_address
    
    def to_dict(self) -> Dict:
        return {
            "amount": self.amount,
            "recipient": self.recipient_address
        }


class Transaction:
    """UTXO-based Transaction."""
    
    def __init__(self, inputs: List[TxInput], outputs: List[TxOutput], 
                 timestamp: float = None, tx_id: str = None):
        self.inputs = inputs
        self.outputs = outputs
        self.timestamp = timestamp or time.time()
        self.tx_id = tx_id or self.compute_hash()
    
    def compute_hash(self) -> str:
        """Compute transaction ID (hash of transaction data)."""
        tx_data = {
            "inputs": [i.to_dict() for i in self.inputs],
            "outputs": [o.to_dict() for o in self.outputs],
            "timestamp": self.timestamp
        }
        return hash_transaction(tx_data)
    
    def sign_input(self, index: int, private_key: SigningKey, utxo_to_spend: UTXO):
        """Sign a specific input with private key."""
        if index >= len(self.inputs):
            raise IndexError("Input index out of bounds")
        
        # Create signing message (simplified - real Bitcoin uses more complex scheme)
        message = f"{utxo_to_spend.tx_id}:{utxo_to_spend.output_index}:{self.timestamp}"
        
        # Sign with ECDSA
        signature = private_key.sign(message.encode(), sigencode=sigencode_der)
        public_key = private_key.get_verifying_key().to_string().hex()
        
        self.inputs[index].signature = signature.hex()
        self.inputs[index].public_key = public_key
        self.tx_id = self.compute_hash()  # Recompute hash after signing
    
    def verify_signature(self, index: int, utxo_to_spend: UTXO) -> bool:
        """Verify signature of a specific input."""
        if index >= len(self.inputs):
            return False
        
        input_obj = self.inputs[index]
        if not input_obj.signature or not input_obj.public_key:
            return False
        
        try:
            message = f"{utxo_to_spend.tx_id}:{utxo_to_spend.output_index}:{self.timestamp}"
            signature = bytes.fromhex(input_obj.signature)
            public_key = VerifyingKey.from_string(
                bytes.fromhex(input_obj.public_key), 
                curve=SECP256k1
            )
            return public_key.verify(signature, message.encode(), sigdecode=sigdecode_der)
        except:
            return False
    
    def is_coinbase(self) -> bool:
        """Check if this is a coinbase transaction (miner reward)."""
        return len(self.inputs) == 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "tx_id": self.tx_id,
            "inputs": [i.to_dict() for i in self.inputs],
            "outputs": [o.to_dict() for o in self.outputs],
            "timestamp": self.timestamp
        }
    
    @classmethod
    def create_coinbase(cls, miner_address: str, amount: float) -> 'Transaction':
        """Create a coinbase transaction (miner reward)."""
        output = TxOutput(amount, miner_address)
        return cls(inputs=[], outputs=[output])


class UTXOSet:
    """Manages all unspent transaction outputs."""
    
    def __init__(self):
        self.utxos = {}  # {(tx_id, output_index): UTXO}
        self.address_utxos = {}  # {address: set((tx_id, output_index))}
    
    def add_utxo(self, utxo: UTXO):
        """Add a new UTXO to the set."""
        key = (utxo.tx_id, utxo.output_index)
        self.utxos[key] = utxo
        
        # Track by address for quick lookup
        if utxo.recipient_address not in self.address_utxos:
            self.address_utxos[utxo.recipient_address] = set()
        self.address_utxos[utxo.recipient_address].add(key)
    
    def remove_utxo(self, tx_id: str, output_index: int) -> UTXO:
        """Remove a spent UTXO."""
        key = (tx_id, output_index)
        if key in self.utxos:
            utxo = self.utxos[key]
            # Remove from address index
            if utxo.recipient_address in self.address_utxos:
                self.address_utxos[utxo.recipient_address].discard(key)
                if not self.address_utxos[utxo.recipient_address]:
                    del self.address_utxos[utxo.recipient_address]
            return self.utxos.pop(key)
        return None
    
    def get_balance(self, address: str) -> float:
        """Calculate balance for an address."""
        balance = 0.0
        if address in self.address_utxos:
            for key in self.address_utxos[address]:
                utxo = self.utxos[key]
                balance += utxo.amount
        return balance
    
    def find_spendable_utxos(self, address: str, amount: float) -> Tuple[List[UTXO], float]:
        """
        Find UTXOs to spend for a given amount.
        Returns (list of UTXOs, total amount)
        """
        spendable = []
        total = 0.0
        
        if address not in self.address_utxos:
            return [], 0.0
        
        for key in sorted(self.address_utxos[address], 
                         key=lambda k: self.utxos[k].amount, 
                         reverse=True):
            utxo = self.utxos[key]
            spendable.append(utxo)
            total += utxo.amount
            
            if total >= amount:
                break
        
        return spendable, total
    
    def update_with_transaction(self, tx: Transaction):
        """
        Update UTXO set with a new transaction.
        Removes spent UTXOs and adds new ones.
        """
        # Remove inputs (spent UTXOs)
        for tx_input in tx.inputs:
            self.remove_utxo(tx_input.tx_id, tx_input.output_index)
        
        # Add outputs (new UTXOs)
        for i, output in enumerate(tx.outputs):
            utxo = UTXO(
                tx_id=tx.tx_id,
                output_index=i,
                amount=output.amount,
                recipient_address=output.recipient_address,
                is_coinbase=tx.is_coinbase()
            )
            self.add_utxo(utxo)