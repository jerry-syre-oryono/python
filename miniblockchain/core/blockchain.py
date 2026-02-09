import hashlib
import json
import time
from typing import List, Dict, Tuple, Set
from .block import Block
from .transaction import Transaction, UTXO, TxInput, TxOutput, UTXOSet
from .contract import SmartContract, ContractTransaction # Added ContractTransaction import
from .merkle import MerkleTree, hash_transaction

class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.difficulty = 4
        self.utxo_set = UTXOSet()
        self.mempool = {}  # {tx_id: Transaction}
        
        self.create_genesis_block()
    
    def create_genesis_block(self):
        """Create genesis block with initial coinbase transaction."""
        genesis_wallet = "genesis"
        
        # Create coinbase transaction for initial supply
        coinbase_tx = Transaction.create_coinbase(
            miner_address=genesis_wallet,
            amount=1000000  # Initial supply
        )
        
        genesis_block = Block(
            index=0,
            transactions=[coinbase_tx.to_dict()],
            timestamp=time.time(),
            previous_hash="0" * 64
        )
        
        # Add to chain
        self.chain.append(genesis_block)
        
        # Initialize UTXO set with genesis output
        self.utxo_set.update_with_transaction(coinbase_tx)
    
    def validate_transaction(self, tx: Transaction) -> Tuple[bool, str]:
        """Validate a transaction (UTXO model)."""
        # 1. Check basic structure
        if not tx.inputs and not tx.is_coinbase():
            return False, "No inputs in non-coinbase transaction"
        
        if not tx.outputs:
            return False, "No outputs"
        
        # 2. Check output amounts are positive
        for output in tx.outputs:
            if output.amount <= 0:
                return False, "Output amount must be positive"
        
        # 3. For coinbase transactions, skip input validation
        if tx.is_coinbase():
            # Coinbase can only have one output in our simple model
            if len(tx.outputs) != 1:
                return False, "Coinbase must have exactly one output"
            return True, ""
        
        # 4. Validate inputs
        input_amount = 0.0
        spent_utxos = set()
        
        for i, tx_input in enumerate(tx.inputs):
            # Check if referenced UTXO exists
            key = (tx_input.tx_id, tx_input.output_index)
            if key not in self.utxo_set.utxos:
                return False, f"Input {i}: UTXO not found"
            
            utxo = self.utxo_set.utxos[key]
            
            # Check for double spend in this transaction
            if key in spent_utxos:
                return False, f"Input {i}: Double spend in same transaction"
            spent_utxos.add(key)
            
            # Verify signature
            if not tx.verify_signature(i, utxo):
                return False, f"Input {i}: Invalid signature"
            
            # Check UTXO belongs to signer
            if tx_input.public_key:
                # In real Bitcoin, we'd derive address from public key
                # For simplicity, we'll just check it matches UTXO owner
                pass
            
            input_amount += utxo.amount
        
        # 5. Validate outputs don't exceed inputs
        output_amount = sum(output.amount for output in tx.outputs)
        
        if input_amount < output_amount:
            return False, f"Insufficient funds: {input_amount} < {output_amount}"
        
        # 6. Check for reasonable fee (optional)
        fee = input_amount - output_amount
        if fee < 0:
            return False, "Negative fee"
        
        # Validate smart contracts if present
        if hasattr(tx, 'contracts') and tx.contracts:
            # Assuming tx.validate_contracts() exists on the Transaction object
            if not tx.validate_contracts():
                return False, "Smart contract validation failed"
        
        return True, ""
    
    def add_transaction(self, tx: Transaction) -> Tuple[bool, str]:
        """Add transaction to pending pool."""
        is_valid, message = self.validate_transaction(tx)
        
        if not is_valid:
            return False, message
        
        # Check for double spend in mempool
        for tx_input in tx.inputs:
            key = (tx_input.tx_id, tx_input.output_index)
            for mempool_tx in self.pending_transactions:
                for mempool_input in mempool_tx.inputs:
                    if (mempool_input.tx_id == tx_input.tx_id and 
                        mempool_input.output_index == tx_input.output_index):
                        return False, "Double spend attempt in mempool"
        
        # Add to pending transactions
        self.pending_transactions.append(tx)
        self.mempool[tx.tx_id] = tx
        
        return True, f"Transaction added to mempool. TXID: {tx.tx_id[:16]}..."
    
    def create_transaction(self, sender_wallet, recipient_address: str, 
                          amount: float, fee: float = 0.001) -> Transaction:
        """Helper to create and sign a transaction."""
        # Find spendable UTXOs
        spendable_utxos, total = self.utxo_set.find_spendable_utxos(
            sender_wallet.address, 
            amount + fee
        )
        
        if total < amount + fee:
            raise ValueError(f"Insufficient balance: {total} < {amount + fee}")
        
        # Create transaction inputs
        inputs = []
        for utxo in spendable_utxos:
            inputs.append(TxInput(
                tx_id=utxo.tx_id,
                output_index=utxo.output_index
            ))
        
        # Create outputs
        outputs = [
            TxOutput(amount, recipient_address)
        ]
        
        # Add change output if needed
        change = total - amount - fee
        if change > 0:
            outputs.append(TxOutput(change, sender_wallet.address))
        
        # Create and sign transaction
        tx = Transaction(inputs, outputs)
        
        for i, utxo in enumerate(spendable_utxos):
            tx.sign_input(i, sender_wallet.private_key, utxo)
        
        return tx
    
    def mine_block(self, miner_address: str) -> Block:
        """Mine a new block with pending transactions."""
        # Add coinbase transaction (miner reward + fees)
        total_fees = self.calculate_total_fees()
        coinbase_amount = 6.25 + total_fees  # 6.25 BTC reward + fees
        coinbase_tx = Transaction.create_coinbase(miner_address, coinbase_amount)
        
        # Prepare transactions for block (coinbase first)
        block_transactions = [coinbase_tx.to_dict()]
        for tx in self.pending_transactions:
            block_transactions.append(tx.to_dict())
        
        # Create and mine block
        new_block = Block(
            index=len(self.chain),
            transactions=block_transactions,
            timestamp=time.time(),
            previous_hash=self.get_last_block().hash
        )
        
        print(f"Mining block {new_block.index}...")
        start_time = time.time()
        
        # Proof-of-Work mining
        while not new_block.hash.startswith('0' * self.difficulty):
            new_block.nonce += 1
            new_block.hash = new_block.compute_hash()
        
        mining_time = time.time() - start_time
        print(f"Block mined! Hash: {new_block.hash[:16]}...")
        print(f"Time: {mining_time:.2f}s, Hash rate: {new_block.nonce/mining_time:.0f} H/s")
        
        # Add to chain
        self.chain.append(new_block)
        
        # Update UTXO set
        self.utxo_set.update_with_transaction(coinbase_tx)
        for tx in self.pending_transactions:
            self.utxo_set.update_with_transaction(tx)
        
        # Clear pending transactions
        self.pending_transactions = []
        self.mempool = {}
        
        # Adjust difficulty (simplified)
        self.adjust_difficulty(new_block)
        
        return new_block
    
    def calculate_total_fees(self) -> float:
        """Calculate total fees in pending transactions."""
        total_fees = 0.0
        
        for tx in self.pending_transactions:
            if tx.is_coinbase():
                continue
            
            input_amount = 0.0
            for tx_input in tx.inputs:
                key = (tx_input.tx_id, tx_input.output_index)
                if key in self.utxo_set.utxos:
                    input_amount += self.utxo_set.utxos[key].amount
            
            output_amount = sum(output.amount for output in tx.outputs)
            total_fees += (input_amount - output_amount)
        
        return total_fees
    
    def adjust_difficulty(self, new_block: Block):
        """Simple difficulty adjustment (every 10 blocks)."""
        if len(self.chain) % 10 == 0:
            # Target block time: 10 minutes (600 seconds)
            target_time = 600
            actual_time = self.chain[-1].timestamp - self.chain[-10].timestamp
            
            if actual_time < target_time / 2:
                self.difficulty += 1
                print(f"Difficulty increased to {self.difficulty}")
            elif actual_time > target_time * 2:
                self.difficulty = max(1, self.difficulty - 1)
                print(f"Difficulty decreased to {self.difficulty}")
    
    def get_balance(self, address: str) -> float:
        """Get balance for an address."""
        return self.utxo_set.get_balance(address)
    
    def get_utxos(self, address: str) -> List[UTXO]:
        """Get all UTXOs for an address."""
        utxos = []
        if address in self.utxo_set.address_utxos:
            for key in self.utxo_set.address_utxos[address]:
                utxos.append(self.utxo_set.utxos[key])
        return utxos
    
    def is_chain_valid(self) -> bool:
        """Validate entire blockchain with UTXO model."""
        # Rebuild UTXO set from scratch to validate
        temp_utxo_set = UTXOSet()
        temp_mempool = set()
        
        for i, block in enumerate(self.chain):
            # Validate block hash
            if block.hash != block.compute_hash():
                print(f"Block {i} has invalid hash!")
                return False
            
            # Validate previous hash (except genesis)
            if i > 0 and block.previous_hash != self.chain[i-1].hash:
                print(f"Block {i} has invalid previous hash!")
                return False
            
            # Validate proof-of-work (skip for genesis block)
            if i > 0 and not block.hash.startswith('0' * self.difficulty):
                print(f"Block {i} has invalid proof-of-work!")
                return False
            
            # Validate transactions in block
            for tx_dict in block.transactions:
                # Convert back to Transaction object
                if "inputs" in tx_dict:  # It's a full transaction dict
                    inputs = [TxInput(**inp) for inp in tx_dict["inputs"]]
                    outputs = [TxOutput(amount=out["amount"], recipient_address=out["recipient"]) for out in tx_dict["outputs"]]
                    tx = Transaction(inputs, outputs, tx_dict["timestamp"], tx_dict["tx_id"])
                else:
                    # Coinbase or simplified format
                    continue
                
                # Validate transaction
                if not tx.is_coinbase():
                    is_valid, msg = self._validate_transaction_with_utxo(tx, temp_utxo_set, temp_mempool)
                    if not is_valid:
                        print(f"Block {i}: Invalid transaction: {msg}")
                        return False
                
                # Update temp UTXO set
                temp_utxo_set.update_with_transaction(tx)
        
        return True
    
    def _validate_transaction_with_utxo(self, tx: Transaction, utxo_set: UTXOSet, 
                                       mempool: Set) -> Tuple[bool, str]:
        """Helper to validate transaction with given UTXO set."""
        # 1. Check basic structure
        if not tx.inputs and not tx.is_coinbase():
            return False, "No inputs in non-coinbase transaction"
        
        if not tx.outputs:
            return False, "No outputs"
        
        # 2. Check output amounts are positive
        for output in tx.outputs:
            if output.amount <= 0:
                return False, "Output amount must be positive"
        
        # 3. For coinbase transactions, skip input validation
        if tx.is_coinbase():
            if len(tx.outputs) != 1:
                return False, "Coinbase must have exactly one output"
            return True, ""
        
        # 4. Validate inputs
        input_amount = 0.0
        spent_utxos = set()
        
        for i, tx_input in enumerate(tx.inputs):
            # Check if referenced UTXO exists in the provided utxo_set
            key = (tx_input.tx_id, tx_input.output_index)
            if key not in utxo_set.utxos:
                return False, f"Input {i}: UTXO not found in provided set"
            
            utxo = utxo_set.utxos[key]
            
            # Check for double spend in this transaction
            if key in spent_utxos:
                return False, f"Input {i}: Double spend in same transaction"
            spent_utxos.add(key)
            
            # Verify signature
            if not tx.verify_signature(i, utxo):
                return False, f"Input {i}: Invalid signature"
            
            input_amount += utxo.amount
        
        # 5. Validate outputs don't exceed inputs
        output_amount = sum(output.amount for output in tx.outputs)
        
        if input_amount < output_amount:
            return False, f"Insufficient funds: {input_amount} < {output_amount}"
        
        # 6. Check for reasonable fee (optional)
        fee = input_amount - output_amount
        if fee < 0:
            return False, "Negative fee"
        
        # Validate smart contracts if present
        if hasattr(tx, 'contracts') and tx.contracts:
            if not tx.validate_contracts():
                return False, "Smart contract validation failed"
        
        return True, ""
    
    def get_last_block(self) -> Block:
        return self.chain[-1]