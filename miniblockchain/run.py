#!/usr/bin/env python3
"""
Mini Blockchain - Complete Implementation
Run with: python run.py [mode]
Modes: api, p2p, interactive, test
"""

import sys
import os
import argparse
import threading
import time

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miniblockchain.network.api_server import run_api_server
from miniblockchain.network.p2p_node import P2PNode
from miniblockchain.core.blockchain import Blockchain
from miniblockchain.wallet import Wallet
from miniblockchain.core.merkle import MerkleTree
from miniblockchain.core import contract # Changed import

def run_api():
    """Run the web API interface."""
    print("Starting Web API Interface...")
    print("Open http://127.0.0.1:5000 in your browser")
    run_api_server()

def run_p2p():
    """Run the P2P network node."""
    parser = argparse.ArgumentParser(description='P2P Blockchain Node')
    parser.add_argument('--host', default='127.0.0.1', help='Host IP')
    parser.add_argument('--port', type=int, default=6000, help='Port number')
    args = parser.parse_args()
    
    node = P2PNode(host=args.host, port=args.port)
    
    try:
        node.start()
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        node.stop()

def interactive_demo():
    """Run interactive command-line demo."""
    blockchain = Blockchain()
    wallets = {}
    
    print("=" * 60)
    print("MINI BLOCKCHAIN - INTERACTIVE DEMO")
    print("=" * 60)
    print("\nFeatures included:")
    print("✓ UTXO Model (like Bitcoin)")
    print("✓ Merkle Trees for transaction verification")
    print("✓ Smart Contracts (simplified Script)")
    print("✓ Web Interface (Flask)")
    print("✓ P2P Networking (socket-based)")
    
    while True:
        print("\n" + "=" * 40)
        print("MAIN MENU")
        print("=" * 40)
        print("1. Wallet Management")
        print("2. Blockchain Operations")
        print("3. Smart Contracts")
        print("4. Merkle Tree Demo")
        print("5. Network Operations")
        print("6. Exit")
        
        choice = input("\nSelect option: ")
        
        if choice == "1":
            wallet_management(blockchain, wallets)
        elif choice == "2":
            blockchain_operations(blockchain, wallets)
        elif choice == "3":
            smart_contract_demo(blockchain, wallets)
        elif choice == "4":
            merkle_tree_demo()
        elif choice == "5":
            network_operations()
        elif choice == "6":
            print("Goodbye!")
            break

def wallet_management(blockchain, wallets):
    """Wallet management submenu."""
    while True:
        print("\n--- Wallet Management ---")
        print("1. Create new wallet")
        print("2. List wallets")
        print("3. Check balance")
        print("4. Back to main")
        
        choice = input("Select: ")
        
        if choice == "1":
            name = input("Wallet name: ")
            if name in wallets:
                print("Wallet name already exists!")
            else:
                wallet = Wallet()
                wallets[name] = wallet
                print(f"Created wallet '{name}'")
                print(f"Address: {wallet.address}")
                print(f"Public key: {wallet.public_key.to_string().hex()[:64]}...")
        
        elif choice == "2":
            if not wallets:
                print("No wallets created yet.")
            else:
                for name, wallet in wallets.items():
                    balance = blockchain.get_balance(wallet.address)
                    print(f"{name}: {wallet.address[:20]}... (Balance: {balance})")
        
        elif choice == "3":
            name = input("Wallet name: ")
            if name in wallets:
                balance = blockchain.get_balance(wallets[name].address)
                print(f"Balance: {balance}")
                
                # Show UTXOs
                utxos = blockchain.get_utxos(wallets[name].address)
                print(f"UTXOs: {len(utxos)}")
                for utxo in utxos[:3]:  # Show first 3
                    print(f"  {utxo.amount} BTC from {utxo.tx_id[:16]}...")
                if len(utxos) > 3:
                    print(f"  ... and {len(utxos) - 3} more")
            else:
                print("Wallet not found.")
        
        elif choice == "4":
            break

def blockchain_operations(blockchain, wallets):
    """Blockchain operations submenu."""
    while True:
        print("\n--- Blockchain Operations ---")
        print("1. Create transaction")
        print("2. Mine block")
        print("3. View blockchain")
        print("4. Validate chain")
        print("5. Back to main")
        
        choice = input("Select: ")
        
        if choice == "1":
            if len(wallets) < 2:
                print("Need at least 2 wallets to create transaction!")
                continue
            
            print("Available wallets:")
            for name in wallets.keys():
                print(f"  {name}")
            
            sender = input("Sender wallet name: ")
            if sender not in wallets:
                print("Sender not found!")
                continue
            
            recipient = input("Recipient address or wallet name: ")
            if recipient in wallets:
                recipient = wallets[recipient].address
            
            try:
                amount = float(input("Amount: "))
                fee = float(input("Fee (default 0.001): ") or "0.001")
                
                tx = blockchain.create_transaction(
                    wallets[sender],
                    recipient,
                    amount,
                    fee
                )
                
                success, message = blockchain.add_transaction(tx)
                print(message)
                
                if success:
                    print(f"Transaction ID: {tx.tx_id}")
            
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == "2":
            if not wallets:
                print("No wallets available. Create a wallet first.")
                continue
            
            print("Available wallets for mining reward:")
            for name in wallets.keys():
                print(f"  {name}")
            
            miner = input("Miner wallet name: ")
            if miner not in wallets:
                print("Wallet not found!")
                continue
            
            print(f"Mining block #{len(blockchain.chain)}...")
            block = blockchain.mine_block(wallets[miner].address)
            print(f"Block mined! Hash: {block.hash[:20]}...")
            print(f"Block reward: 6.25 BTC + fees")
        
        elif choice == "3":
            print(f"\nBlockchain length: {len(blockchain.chain)} blocks")
            print(f"Difficulty: {blockchain.difficulty}")
            print(f"Pending transactions: {len(blockchain.pending_transactions)}")
            
            # Show last 3 blocks
            for block in blockchain.chain[-3:]:
                print(f"\nBlock #{block.index}:")
                print(f"  Hash: {block.hash[:20]}...")
                print(f"  Previous: {block.previous_hash[:20]}...")
                print(f"  Transactions: {len(block.transactions)}")
                print(f"  Merkle root: {block.merkle_root[:20]}...")
                print(f"  Nonce: {block.nonce}")
        
        elif choice == "4":
            is_valid = blockchain.is_chain_valid()
            print(f"Blockchain valid: {is_valid}")
        
        elif choice == "5":
            break

def smart_contract_demo(blockchain, wallets):
    """Smart contract demonstration."""
    print("\n--- Smart Contract Demo ---")
    print("Creating a simple multisig contract...")
    
    # Create 3 wallets for multisig
    if len(wallets) < 3:
        print("Need at least 3 wallets for multisig demo.")
        return
    
    # Take first 3 wallets
    wallet_names = list(wallets.keys())[:3]
    wallet_objs = [wallets[name] for name in wallet_names]
    
    print(f"Using wallets: {', '.join(wallet_names)}")
    
    # Create multisig contract (2-of-3)
    public_keys = [wallet.public_key.to_string() for wallet in wallet_objs]
    contract_obj = contract.SmartContract.create_multisig_contract(public_keys, 2) # Changed
    
    print("Multisig contract created (2-of-3)")
    print("Contract script size:", len(contract_obj.locking_script.script_bytes), "bytes") # Changed
    
    # Simulate validation
    print("\nSimulating contract validation...")
    
    # Create fake transaction context
    tx_context = {"amount": 1.0, "timestamp": time.time()}
    
    # Would need signatures from 2 of 3 wallets to validate
    print("Contract would require signatures from 2 of the 3 wallets.")
    print("Try implementing the signing logic as an exercise!")

def merkle_tree_demo():
    """Merkle tree demonstration."""
    print("\n--- Merkle Tree Demo ---")
    
    # Create sample transactions
    transactions = [
        {"from": "alice", "to": "bob", "amount": 1.0},
        {"from": "bob", "to": "charlie", "amount": 2.0},
        {"from": "charlie", "to": "david", "amount": 0.5},
        {"from": "david", "to": "alice", "amount": 1.5},
    ]
    
    # Hash transactions
    from miniblockchain.core.merkle import MerkleTree, hash_transaction
    tx_hashes = [hash_transaction(tx) for tx in transactions]
    
    # Build Merkle tree
    merkle_tree = MerkleTree(tx_hashes)
    
    print("Transactions:")
    for i, tx in enumerate(transactions):
        print(f"  {i}: {tx['from']} -> {tx['to']}: {tx['amount']}")
        print(f"     Hash: {tx_hashes[i][:16]}...")
    
    print(f"\nMerkle Root: {merkle_tree.root[:20]}...")
    print("\nTree structure:")
    print(merkle_tree.visualize())
    
    # Demonstrate proof
    print("\n--- Merkle Proof Demo ---")
    print("Proving inclusion of transaction 1...")
    
    proof = merkle_tree.get_proof(1)
    print(f"Proof length: {len(proof)} steps")
    
    for i, (sibling_hash, is_left) in enumerate(proof):
        position = "left" if is_left else "right"
        print(f"  Step {i}: {sibling_hash[:16]}... ({position})")
    
    # Verify proof
    is_valid = MerkleTree.verify_proof(tx_hashes[1], proof, merkle_tree.root)
    print(f"\nProof valid: {is_valid}")

def network_operations():
    """Network operations submenu."""
    print("\n--- Network Operations ---")
    print("P2P networking requires running multiple nodes.")
    print("\nTo test the network:")
    print("1. Open terminal 1: python run.py p2p --port 6001")
    print("2. Open terminal 2: python run.py p2p --port 6002")
    print("3. Open terminal 3: python run.py p2p --port 6003")
    print("\nThey will automatically connect and sync blocks.")

def run_tests():
    """Run comprehensive tests."""
    print("Running tests...")
    
    # Import and run tests
    import unittest
    from tests.test_blockchain import TestBlockchain
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBlockchain)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\nTests passed: {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Mini Blockchain')
    parser.add_argument('mode', nargs='?', default='interactive',
                       choices=['api', 'p2p', 'interactive', 'test'],
                       help='Run mode (default: interactive)')
    
    args = parser.parse_args()
    
    if args.mode == 'api':
        run_api()
    elif args.mode == 'p2p':
        run_p2p()
    elif args.mode == 'interactive':
        interactive_demo()
    elif args.mode == 'test':
        run_tests()
    else:
        print("Invalid mode. Use: api, p2p, interactive, or test")