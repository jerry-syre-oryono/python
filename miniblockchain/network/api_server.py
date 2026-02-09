from flask import Flask, jsonify, request, render_template_string
import json
import threading
import time
from typing import Dict, Any

from miniblockchain.core.blockchain import Blockchain
from miniblockchain.wallet import Wallet
from miniblockchain.core.transaction import Transaction, TxInput, TxOutput

app = Flask(__name__)
blockchain = Blockchain()
wallets = {}  # name -> Wallet object

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Mini Blockchain Explorer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .card { border: 1px solid #ddd; padding: 20px; margin: 10px 0; border-radius: 5px; }
        .success { background: #d4edda; }
        .error { background: #f8d7da; }
        .block { background: #e9ecef; }
        .tx { background: #fff3cd; }
        input, button { margin: 5px; padding: 8px; }
    </style>
</head>
<body>
    <h1>🔗 Mini Blockchain Explorer</h1>
    
    <div class="card">
        <h2>💰 Wallet Management</h2>
        <form action="/create_wallet" method="post">
            <input type="text" name="name" placeholder="Wallet name" required>
            <button type="submit">Create Wallet</button>
        </form>
        
        {% if wallets %}
        <h3>Existing Wallets:</h3>
        <ul>
            {% for name, wallet in wallets.items() %}
            <li>{{ name }}: {{ wallet.address[:20] }}... (Balance: {{ balances.get(wallet.address, 0) }})</li>
            {% endfor %}
        </ul>
        {% endif %}
    </div>
    
    <div class="card">
        <h2>📤 Create Transaction</h2>
        <form action="/create_transaction" method="post">
            <input type="text" name="sender" placeholder="Sender wallet name" required>
            <input type="text" name="recipient" placeholder="Recipient address" required>
            <input type="number" name="amount" placeholder="Amount" step="0.000001" required>
            <input type="number" name="fee" placeholder="Fee" value="0.001" step="0.000001">
            <button type="submit">Send</button>
        </form>
    </div>
    
    <div class="card">
        <h2>⛏️ Mining</h2>
        <form action="/mine" method="post">
            <input type="text" name="miner" placeholder="Miner wallet name" required>
            <button type="submit">Mine Block</button>
        </form>
        <p>Pending transactions: {{ blockchain.pending_transactions|length }}</p>
    </div>
    
    <div class="card">
        <h2>🔍 Blockchain Info</h2>
        <p>Chain length: {{ blockchain.chain|length }} blocks</p>
        <p>Difficulty: {{ blockchain.difficulty }}</p>
        <p>Chain valid: {{ blockchain.is_chain_valid() }}</p>
        
        <h3>Latest Blocks:</h3>
        {% for block in blockchain.chain[-5:]|reverse %}
        <div class="block">
            <strong>Block #{{ block.index }}</strong><br>
            Hash: {{ block.hash[:20] }}...<br>
            Previous: {{ block.previous_hash[:20] }}...<br>
            Transactions: {{ block.transactions|length }}<br>
            Nonce: {{ block.nonce }}
        </div>
        {% endfor %}
    </div>
    
    {% if message %}
    <div class="card {{ 'success' if 'success' in message.lower() else 'error' }}">
        {{ message }}
    </div>
    {% endif %}
</body>
</html>
"""

@app.route('/')
def index():
    """Main explorer page."""
    balances = {}
    for name, wallet in wallets.items():
        balances[wallet.address] = blockchain.get_balance(wallet.address)
    
    return render_template_string(HTML_TEMPLATE, 
                                 blockchain=blockchain,
                                 wallets=wallets,
                                 balances=balances,
                                 message=request.args.get('message', ''))

@app.route('/api/chain', methods=['GET'])
def get_chain():
    """Get full blockchain."""
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.to_dict())
    
    return jsonify({
        "length": len(blockchain.chain),
        "chain": chain_data
    })

@app.route('/api/block/<int:index>', methods=['GET'])
def get_block(index):
    """Get specific block."""
    if index < 0 or index >= len(blockchain.chain):
        return jsonify({"error": "Block not found"}), 404
    
    return jsonify(blockchain.chain[index].to_dict())

@app.route('/api/transaction/<tx_id>', methods=['GET'])
def get_transaction(tx_id):
    """Get transaction by ID."""
    # Search in blockchain
    for block in blockchain.chain:
        for tx_dict in block.transactions:
            if tx_dict.get('tx_id', '').startswith(tx_id):
                return jsonify(tx_dict)
    
    # Search in mempool
    if tx_id in blockchain.mempool:
        return jsonify(blockchain.mempool[tx_id].to_dict())
    
    return jsonify({"error": "Transaction not found"}), 404

@app.route('/api/balance/<address>', methods=['GET'])
def get_balance(address):
    """Get balance for address."""
    balance = blockchain.get_balance(address)
    utxos = blockchain.get_utxos(address)
    
    return jsonify({
        "address": address,
        "balance": balance,
        "utxo_count": len(utxos),
        "utxos": [utxo.to_dict() for utxo in utxos[:10]]  # Limit to 10
    })

@app.route('/create_wallet', methods=['POST'])
def create_wallet():
    """Create a new wallet."""
    name = request.form.get('name')
    if not name:
        return jsonify({"error": "Name required"}), 400
    
    if name in wallets:
        return jsonify({"error": "Wallet name already exists"}), 400
    
    wallet = Wallet()
    wallets[name] = wallet
    
    return jsonify({
        "name": name,
        "address": wallet.address,
        "public_key": wallet.public_key.to_string().hex(),
        "message": f"Wallet '{name}' created successfully"
    })

@app.route('/create_transaction', methods=['POST'])
def create_transaction():
    """Create and broadcast a transaction."""
    sender_name = request.form.get('sender')
    recipient = request.form.get('recipient')
    amount = float(request.form.get('amount', 0))
    fee = float(request.form.get('fee', 0.001))
    
    if sender_name not in wallets:
        return jsonify({"error": "Sender wallet not found"}), 400
    
    try:
        # Create transaction
        tx = blockchain.create_transaction(
            wallets[sender_name],
            recipient,
            amount,
            fee
        )
        
        # Add to blockchain
        success, message = blockchain.add_transaction(tx)
        
        if success:
            # Broadcast to network (in real implementation)
            return jsonify({
                "success": True,
                "message": message,
                "tx_id": tx.tx_id
            })
        else:
            return jsonify({"error": message}), 400
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/mine', methods=['POST'])
def mine_block():
    """Mine a new block."""
    miner_name = request.form.get('miner')
    
    if miner_name not in wallets:
        return jsonify({"error": "Miner wallet not found"}), 400
    
    # Mine block
    new_block = blockchain.mine_block(wallets[miner_name].address)
    
    # Broadcast to network (in real implementation)
    
    return jsonify({
        "success": True,
        "message": f"Block #{new_block.index} mined successfully!",
        "block": new_block.to_dict(),
        "reward": 6.25 + blockchain.calculate_total_fees()
    })

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """Get list of connected nodes."""
    # In real implementation, would return actual connected nodes
    return jsonify({"nodes": list(blockchain.nodes)})

@app.route('/api/nodes/register', methods=['POST'])
def register_node():
    """Register a new node."""
    data = request.get_json()
    node_address = data.get('address')
    
    if not node_address:
        return jsonify({"error": "Address required"}), 400
    
    blockchain.register_node(node_address)
    return jsonify({"message": f"Node {node_address} registered"})

def run_api_server(host='127.0.0.1', port=5000):
    """Run the Flask API server."""
    print(f"Starting API server at http://{host}:{port}")
    app.run(host=host, port=port, debug=True, use_reloader=False)