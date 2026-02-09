from blockchain import Blockchain
from wallet import Wallet

def interactive_mode():
    blockchain = Blockchain()
    wallets = {}
    
    while True:
        print("\n=== Mini Blockchain ===")
        print("1. Create wallet")
        print("2. Check balance")
        print("3. Send transaction")
        print("4. Mine block")
        print("5. View blockchain")
        print("6. Validate chain")
        print("7. Exit")
        
        choice = input("Choose: ")
        
        if choice == "1":
            name = input("Wallet name: ")
            wallets[name] = Wallet()
            print(f"Created wallet: {wallets[name].address[:20]}...")
            
        elif choice == "2":
            name = input("Wallet name: ")
            if name in wallets:
                balance = blockchain.get_balance(wallets[name].address)
                print(f"Balance: {balance}")
            else:
                print("Wallet not found")
                
        # ... add other options

if __name__ == "__main__":
    interactive_mode()