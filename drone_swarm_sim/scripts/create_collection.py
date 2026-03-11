#!/usr/bin/env python3
"""
Create Qdrant collection for drone swarm
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from config.settings import Config

def create_collection():
    """Create drone_swarm_faces collection in Qdrant"""
    
    config = Config()
    
    # Qdrant connection
    host = os.getenv("QDRANT_HOST", "localhost")
    port = os.getenv("QDRANT_PORT", "6333")
    collection = os.getenv("QDRANT_COLLECTION", "drone_swarm_faces")
    
    base_url = f"http://{host}:{port}"
    
    print(f"🔧 Creating collection '{collection}' in Qdrant at {host}:{port}")
    
    # Collection configuration
    collection_config = {
        "name": collection,
        "vectors": {
            "size": config.EMBEDDING_SIZE,
            "distance": "Cosine"
        },
        "optimizers_config": {
            "default_segment_number": 5,
            "indexing_threshold": 10000,
            "memmap_threshold": 20000
        },
        "hnsw_config": {
            "m": 16,
            "ef_construct": 100,
            "full_scan_threshold": 10000
        }
    }
    
    # Check if collection exists
    response = requests.get(f"{base_url}/collections")
    
    if response.status_code == 200:
        collections = response.json()["result"]["collections"]
        existing = [c["name"] for c in collections]
        
        if collection in existing:
            print(f"✅ Collection '{collection}' already exists")
            
            # Show collection info
            info = requests.get(f"{base_url}/collections/{collection}")
            if info.status_code == 200:
                data = info.json()["result"]
                print(f"   Vectors: {data['vectors_count']}")
                print(f"   Segments: {data['segments_count']}")
                print(f"   Status: {data['status']}")
            return
    
    # Create collection
    response = requests.put(
        f"{base_url}/collections/{collection}",
        json=collection_config
    )
    
    if response.status_code == 200:
        print(f"✅ Successfully created collection '{collection}'")
        
        # Create payload indexes
        print("📊 Creating payload indexes...")
        
        # Person ID index
        requests.put(
            f"{base_url}/collections/{collection}/index",
            json={
                "field_name": "person_id",
                "field_type": "keyword"
            }
        )
        
        # Drone ID index
        requests.put(
            f"{base_url}/collections/{collection}/index",
            json={
                "field_name": "drone_id",
                "field_type": "integer"
            }
        )
        
        print("✅ Payload indexes created")
    else:
        print(f"❌ Failed to create collection: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    create_collection()