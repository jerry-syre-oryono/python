#!/bin/bash

echo "🚁 Drone Swarm System Setup"
echo "=========================="

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directory structure..."
mkdir -p data/qdrant_storage
mkdir -p data/logs
mkdir -p data/models
mkdir -p configs

# Set up environment
echo "🔧 Setting up environment..."
cp .env.example .env

# Check Qdrant
echo "🔍 Checking Qdrant..."
if command -v docker &> /dev/null; then
    if ! curl -s http://localhost:6333/healthz > /dev/null; then
        echo "🐳 Starting Qdrant container..."
        docker run -d --name qdrant \
            -p 6333:6333 \
            -p 6334:6334 \
            -v $(pwd)/data/qdrant_storage:/qdrant/storage \
            qdrant/qdrant
    else
        echo "✅ Qdrant already running"
    fi
else
    echo "⚠️ Docker not found. Please install Docker or start Qdrant manually."
fi

# Create Qdrant collection
echo "🗄️ Creating drone_swarm_faces collection..."
python scripts/create_collection.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your settings"
echo "2. Run tests: pytest tests/"
echo "3. Start simulation: python main.py"