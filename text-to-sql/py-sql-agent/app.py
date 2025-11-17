"""Flask backend for SQL Agent"""
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from agent import run_agent
import json
import os

app = Flask(__name__, template_folder='templates')
CORS(app)

@app.route('/')
def index():
    """Serve the frontend"""
    return render_template('index.html')

@app.route('/api/query', methods=['POST'])
def execute_query():
    """Execute a query through the agent"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Query cannot be empty'}), 400
        
        result = run_agent(query)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
