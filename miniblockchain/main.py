import json
from miniblockchain.core.blockchain import Blockchain, Block
from miniblockchain.wallet import Wallet
from miniblockchain.core.transaction import Transaction, TxInput, TxOutput
from miniblockchain.p2p import P2PNetwork
import time

def demonstrate_blockchain():
    print("=" * 60)
    print("MINI BLOCKCHAIN DEMONSTRATION")
    print("=" * 60)
    
    # 1. Create wallets (demonstrates public-key cryptography)
    print("\n1. Creating Wallets...")
    alice_wallet = Wallet()
    bob_wallet = Wallet()
    miner_wallet = Wallet()
    
    print(f"Alice's address: {alice_wallet.address[:20]}...")
    print(f"Bob's address: {bob_wallet.address[:20]}...")
    print(f"Miner's address: {miner_wallet.address[:20]}...")
    
    # 2. Create blockchain
    print("\n2. Creating Blockchain with Genesis Block...")
    blockchain = Blockchain()
    print(f"Genesis block hash: {blockchain.chain[0].hash[:20]}...")
    
    # 3. Mine a block to give the miner some funds
    print("\n3. Miner mining a block to get coinbase reward...")
    mined_block = blockchain.mine_block(miner_wallet.address)
    print(f"Mined block: {mined_block.hash[:20]}...")
    print(f"Miner balance after mining: {blockchain.get_balance(miner_wallet.address):.2f}")

    # 4. Miner sends some funds to Alice
    print("\n4. Miner sending funds to Alice...")
    miner_to_alice_tx = blockchain.create_transaction(miner_wallet, alice_wallet.address, 5.0)
    blockchain.add_transaction(miner_to_alice_tx)
    print("Miner-to-Alice transaction added to mempool.")

    # 5. Mine another block to include the miner-to-alice transaction
    print("\n5. Miner mining another block to confirm transfer to Alice...")
    mined_block_2 = blockchain.mine_block(miner_wallet.address)
    print(f"Mined block: {mined_block_2.hash[:20]}...")
    print(f"Alice balance after miner's transfer: {blockchain.get_balance(alice_wallet.address):.2f}")

    # 6. Create and sign a transaction (demonstrates digital signatures)
    print("\n6. Creating Transaction (Alice to Bob)...")
    tx = blockchain.create_transaction(alice_wallet, bob_wallet.address, 2.0)
    
    print(f"Transaction (Alice to Bob) TXID: {tx.tx_id[:10]}...")
    print(f"Amount: {tx.outputs[0].amount}")

    
    # 4. Add transaction to pending pool
    print("\n4. Adding Transaction to Pending Pool...")
    blockchain.add_transaction(tx)
    print(f"Pending transactions: {len(blockchain.pending_transactions)}")
    
    # 5. Mine a block (demonstrates proof-of-work)
    print("\n5. Mining Block (Proof-of-Work)...")
    print(f"Difficulty: {blockchain.difficulty} leading zeros required")
    
    mined_block = blockchain.mine_block(miner_wallet.address)
    print(f"Mined block: {mined_block.hash[:20]}...")
    print(f"Nonce found: {mined_block.nonce}")
    
    # 6. Check balances
    print("\n6. Checking Balances...")
    print(f"Alice balance: {blockchain.get_balance(alice_wallet.address):.2f}")
    print(f"Bob balance: {blockchain.get_balance(bob_wallet.address):.2f}")
    print(f"Miner balance: {blockchain.get_balance(miner_wallet.address):.2f} (reward + fees)")
    
    # 7. Validate chain integrity
    print("\n7. Validating Blockchain Integrity...")
    print(f"Chain length: {len(blockchain.chain)} blocks")
    print(f"Chain valid: {blockchain.is_chain_valid()}")
    
    # 8. Demonstrate tamper detection
    print("\n8. Demonstrating Tamper Detection...")
    print("Attempting to tamper with block 1 transactions...")
    
    # Try to tamper
    original_transaction = blockchain.chain[1].transactions[0]
    blockchain.chain[1].transactions[0] = {"from": "hacker", "to": "hacker", "amount": 1000}
    
    print(f"Chain valid after tampering: {blockchain.is_chain_valid()}")
    
    # Restore original
    blockchain.chain[1].transactions[0] = original_transaction
    print(f"Chain valid after restoration: {blockchain.is_chain_valid()}")
    
    # 9. Print the chain
    print("\n9. Final Blockchain:")
    for i, block in enumerate(blockchain.chain):
        print(f"\nBlock {i}:")
        print(f"  Hash: {block.hash[:20]}...")
        print(f"  Previous: {block.previous_hash[:20]}...")
        print(f"  Nonce: {block.nonce}")
        print(f"  Transactions: {len(block.transactions)}")
        if i > 0: # Skip genesis block for transaction printing
            for j, tx_dict in enumerate(block.transactions):
                if j == 0 and tx_dict.get('inputs') == []: # This is a coinbase transaction
                    # Coinbase transactions have no 'from'
                    recipient = tx_dict['outputs'][0]['recipient'][:10] + '...'
                    amount = tx_dict['outputs'][0]['amount']
                    print(f"    Coinbase -> {recipient}: {amount}")
                else: # Regular transaction
                    # Infer sender from first input's public key (simplified)
                    sender = "unknown"
                    if tx_dict.get('inputs') and tx_dict['inputs'][0].get('public_key'):
                        # In a real app, you'd hash the public key to get an address
                        sender = tx_dict['inputs'][0]['public_key'][:10] + '...'
                    
                    # Get recipient and amount from first output
                    recipient = tx_dict['outputs'][0]['recipient'][:10] + '...'
                    amount = tx_dict['outputs'][0]['amount']
                    print(f"    {sender} -> {recipient}: {amount} (TXID: {tx_dict['tx_id'][:10]}...)")

if __name__ == "__main__":
    demonstrate_blockchain()