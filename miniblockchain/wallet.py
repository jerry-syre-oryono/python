import hashlib
import json
import time
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa.util import sigencode_der, sigdecode_der

class Wallet:
    def __init__(self):
        # SECP256k1 is the same curve Bitcoin uses
        self.private_key = SigningKey.generate(curve=SECP256k1)
        self.public_key = self.private_key.get_verifying_key()
        self.address = self.generate_address()
    
    def generate_address(self) -> str:
        """Generate a shorter address from public key (simplified version)."""
        # In real Bitcoin: SHA256(RIPEMD160(public_key))
        public_key_bytes = self.public_key.to_string()
        return hashlib.sha256(public_key_bytes).hexdigest()[:40]  # First 40 chars
    
    def sign_transaction(self, transaction: Dict) -> str:
        """Sign a transaction with private key."""
        transaction_string = json.dumps(transaction, sort_keys=True)
        signature = self.private_key.sign(transaction_string.encode(), sigencode=sigencode_der)
        return signature.hex()
    
    @staticmethod
    def verify_transaction(transaction: Dict, signature_hex: str, public_key_hex: str) -> bool:
        """Verify a transaction signature."""
        try:
            transaction_string = json.dumps(transaction, sort_keys=True)
            signature = bytes.fromhex(signature_hex)
            public_key = VerifyingKey.from_string(bytes.fromhex(public_key_hex), curve=SECP256k1)
            return public_key.verify(signature, transaction_string.encode(), sigdecode=sigdecode_der)
        except:
            return False

class Transaction:
    def __init__(self, sender_wallet: Wallet, recipient_address: str, amount: float):
        self.sender_address = sender_wallet.address
        self.sender_public_key = sender_wallet.public_key.to_string().hex()
        self.recipient_address = recipient_address
        self.amount = amount
        self.timestamp = time.time()
        self.signature = None
    
    def to_dict(self) -> Dict:
        return {
            "from": self.sender_address,
            "to": self.recipient_address,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "public_key": self.sender_public_key
        }
    
    def sign(self, wallet: Wallet):
        """Sign the transaction with sender's wallet."""
        transaction_data = self.to_dict()
        self.signature = wallet.sign_transaction(transaction_data)
    
    def is_valid(self) -> bool:
        """Verify the transaction signature."""
        if self.signature is None:
            return False
        
        transaction_data = self.to_dict()
        return Wallet.verify_transaction(
            transaction_data,
            self.signature,
            self.sender_public_key
        )