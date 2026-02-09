import hashlib
import json
from typing import List, Dict, Any, Callable
from ecdsa import VerifyingKey, SECP256k1
from ecdsa.util import sigdecode_der
from .transaction import Transaction # Import Transaction class

class VMError(Exception):
    """Virtual Machine error."""
    pass

class OpCode:
    """Operation codes for our simple scripting language."""
    # Stack operations
    OP_DUP = 0x76
    OP_HASH160 = 0xa9
    OP_EQUALVERIFY = 0x88
    OP_CHECKSIG = 0xac
    OP_CHECKMULTISIG = 0xae
    
    # Flow control
    OP_IF = 0x63
    OP_ELSE = 0x67
    OP_ENDIF = 0x68
    OP_VERIFY = 0x69
    
    # Arithmetic
    OP_ADD = 0x93
    OP_EQUAL = 0x87
    
    # Constants
    OP_PUSHDATA = 0x01
    OP_TRUE = 0x51
    OP_FALSE = 0x00

class Script:
    """Smart contract script (inspired by Bitcoin Script)."""
    
    def __init__(self, script_bytes: bytes = None):
        self.script_bytes = script_bytes or b""
        self.program_counter = 0
    
    def add_op(self, opcode: int):
        """Add an opcode to the script."""
        self.script_bytes += bytes([opcode])
    
    def add_data(self, data: bytes):
        """Add data to the script."""
        if len(data) <= 75:
            self.script_bytes += bytes([len(data)]) + data
        else:
            # For larger data (simplified)
            self.script_bytes += bytes([OPCode.OP_PUSHDATA]) + data
    
    def execute(self, stack: List[bytes], tx_context: Dict = None) -> bool:
        """
        Execute the script.
        Returns True if script validates successfully.
        """
        self.program_counter = 0
        alt_stack = []
        if_stack = []  # Track if/else branches
        
        while self.program_counter < len(self.script_bytes):
            opcode = self.script_bytes[self.program_counter]
            self.program_counter += 1
            
            # Skip execution if we're in a false branch
            if if_stack and not if_stack[-1]:
                if opcode == OPCode.OP_ELSE:
                    if_stack[-1] = True  # Switch to else branch
                elif opcode == OPCode.OP_ENDIF:
                    if_stack.pop()
                continue
            
            if opcode <= 0x4e:  # Push data
                if opcode <= 75:
                    data_length = opcode
                else:
                    # Handle extended pushes (simplified)
                    data_length = self.script_bytes[self.program_counter]
                    self.program_counter += 1
                
                data = self.script_bytes[self.program_counter:self.program_counter + data_length]
                self.program_counter += data_length
                stack.append(data)
            
            elif opcode == OPCode.OP_DUP:
                if len(stack) < 1:
                    raise VMError("Stack underflow")
                stack.append(stack[-1])
            
            elif opcode == OPCode.OP_HASH160:
                if len(stack) < 1:
                    raise VMError("Stack underflow")
                data = stack.pop()
                sha256_hash = hashlib.sha256(data).digest()
                ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
                stack.append(ripemd160_hash)
            
            elif opcode == OPCode.OP_EQUALVERIFY:
                if len(stack) < 2:
                    raise VMError("Stack underflow")
                if stack.pop() != stack.pop():
                    return False
            
            elif opcode == OPCode.OP_CHECKSIG:
                if len(stack) < 2:
                    raise VMError("Stack underflow")
                public_key_bytes = stack.pop()
                signature_bytes = stack.pop()
                
                # Verify ECDSA signature
                try:
                    tx_data = json.dumps(tx_context or {}, sort_keys=True).encode()
                    public_key = VerifyingKey.from_string(public_key_bytes, curve=SECP256k1)
                    # Note: In real Bitcoin, the message is more complex
                    if public_key.verify(signature_bytes, tx_data, sigdecode=sigdecode_der):
                        stack.append(b"\x01")  # True
                    else:
                        stack.append(b"\x00")  # False
                except:
                    stack.append(b"\x00")
            
            elif opcode == OPCode.OP_ADD:
                if len(stack) < 2:
                    raise VMError("Stack underflow")
                a = int.from_bytes(stack.pop(), 'big')
                b = int.from_bytes(stack.pop(), 'big')
                stack.append((a + b).to_bytes(32, 'big'))
            
            elif opcode == OPCode.OP_EQUAL:
                if len(stack) < 2:
                    raise VMError("Stack underflow")
                if stack.pop() == stack.pop():
                    stack.append(b"\x01")
                else:
                    stack.append(b"\x00")
            
            elif opcode == OPCode.OP_IF:
                if len(stack) < 1:
                    raise VMError("Stack underflow")
                condition = stack.pop()
                if_stack.append(condition != b"\x00")
            
            elif opcode == OPCode.OP_ELSE:
                if not if_stack:
                    raise VMError("OP_ELSE without OP_IF")
                if_stack[-1] = not if_stack[-1]
            
            elif opcode == OPCode.OP_ENDIF:
                if not if_stack:
                    raise VMError("OP_ENDIF without OP_IF")
                if_stack.pop()
            
            elif opcode == OPCode.OP_VERIFY:
                if len(stack) < 1:
                    raise VMError("Stack underflow")
                if stack.pop() == b"\x00":
                    return False
            
            else:
                raise VMError(f"Unknown opcode: {opcode:02x}")
        
        # Final stack must have a true value
        if not stack:
            return False
        return stack[-1] != b"\x00"


class SmartContract:
    """Represents a smart contract with locking and unlocking scripts."""
    
    def __init__(self, locking_script: Script, unlocking_script: Script = None):
        self.locking_script = locking_script
        self.unlocking_script = unlocking_script or Script()
    
    def validate(self, tx_context: Dict = None) -> bool:
        """Validate the contract by executing both scripts."""
        # Create combined script (unlocking + locking)
        combined_bytes = self.unlocking_script.script_bytes + self.locking_script.script_bytes
        combined_script = Script(combined_bytes)
        
        # Execute with empty stack
        try:
            return combined_script.execute([], tx_context)
        except VMError as e:
            print(f"Script execution error: {e}")
            return False
    
    @classmethod
    def create_p2pkh_contract(cls, recipient_hash: bytes) -> 'SmartContract':
        """Create Pay-to-Public-Key-Hash contract (standard Bitcoin transaction)."""
        script = Script()
        script.add_op(OPCode.OP_DUP)
        script.add_op(OPCode.OP_HASH160)
        script.add_data(recipient_hash)
        script.add_op(OPCode.OP_EQUALVERIFY)
        script.add_op(OPCode.OP_CHECKSIG)
        return cls(script)
    
    @classmethod
    def create_multisig_contract(cls, public_keys: List[bytes], required: int) -> 'SmartContract':
        """Create M-of-N multisig contract."""
        script = Script()
        script.add_data(bytes([required]))
        for pubkey in public_keys:
            script.add_data(pubkey)
        script.add_data(bytes([len(public_keys)]))
        script.add_op(OPCode.OP_CHECKMULTISIG)
        return cls(script)
    
    @classmethod
    def create_htlc_contract(cls, recipient_hash: bytes, sender_hash: bytes, 
                            locktime: int) -> 'SmartContract':
        """
        Create Hashed Timelock Contract (HTLC) for atomic swaps.
        Can be claimed by:
        1. Recipient with secret that hashes to recipient_hash (before locktime)
        2. Sender after locktime
        """
        script = Script()
        
        # OP_IF: Claim by recipient with secret
        script.add_op(OPCode.OP_IF)
        script.add_op(OPCode.OP_HASH160)
        script.add_data(recipient_hash)
        script.add_op(OPCode.OP_EQUALVERIFY)
        script.add_op(OPCode.OP_DUP)
        script.add_op(OPCode.OP_HASH160)
        script.add_op(OPCode.OP_EQUALVERIFY)
        script.add_op(OPCode.OP_CHECKSIG)
        
        # OP_ELSE: Claim by sender after locktime
        script.add_op(OPCode.OP_ELSE)
        script.add_data(locktime.to_bytes(4, 'big'))
        script.add_op(OPCode.OP_CHECKLOCKTIMEVERIFY)
        script.add_op(OPCode.OP_DROP)
        script.add_op(OPCode.OP_DUP)
        script.add_op(OPCode.OP_HASH160)
        script.add_data(sender_hash)
        script.add_op(OPCode.OP_EQUALVERIFY)
        script.add_op(OPCode.OP_CHECKSIG)
        
        script.add_op(OPCode.OP_ENDIF)
        
        return cls(script)


class ContractTransaction(Transaction):
    """Transaction with smart contract support."""
    
    def __init__(self, inputs: List[TxInput], outputs: List[TxOutput], 
                 contracts: List[SmartContract] = None, **kwargs):
        super().__init__(inputs, outputs, **kwargs)
        self.contracts = contracts or []
    
    def validate_contracts(self) -> bool:
        """Validate all smart contracts in the transaction."""
        tx_context = self.to_dict()
        
        for contract in self.contracts:
            if not contract.validate(tx_context):
                return False
        
        return True
    
    def add_contract_output(self, amount: float, contract: SmartContract) -> int:
        """Add an output locked by a smart contract."""
        # In real implementation, contract would be serialized to scriptPubKey
        # For simplicity, we'll store contract in output metadata
        output = TxOutput(amount, f"contract:{contract.locking_script.script_bytes.hex()}")
        self.outputs.append(output)
        self.contracts.append(contract)
        return len(self.outputs) - 1