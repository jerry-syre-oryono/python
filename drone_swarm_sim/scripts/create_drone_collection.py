#!/usr/bin/env python
"""
Create drone_swarm_faces collection in existing Qdrant container
"""
import requests
import sys
import json

def create_drone_collection():
    """Create drone_swarm_faces collection in existing Qdrant"""
    
    host = "localhost"
    port = 6333
    collection = "drone_swarm_faces"
    
    base_url = f"http://{host}:{port}"
    
    print(f"🔧 Creating collection '{collection}' in Qdrant at {host}:{port}")
    print("-" * 50)
    
    # First, check if collection already exists
    try:
        response = requests.get(f"{base_url}/collections")
        if response.status_code == 200:
            collections = response.json()["result"]["collections"]
            existing = [c["name"] for c in collections]
            
            print(f"📚 Existing collections: {existing}")
            
            if collection in existing:
                print(f"✅ Collection '{collection}' already exists!")
                
                # Show collection info
                info = requests.get(f"{base_url}/collections/{collection}")
                if info.status_code == 200:
                    data = info.json()["result"]
                    print(f"   Vectors: {data['points_count']}")
                    print(f"   Segments: {data['segments_count']}")
                    print(f"   Status: {data['status']}")
                return True
    except Exception as e:
        print(f"❌ Cannot connect to Qdrant: {e}")
        print("   Make sure your container is running: docker start qdrant")
        return False
    
    # Collection configuration for face embeddings
    collection_config = {
        "name": collection,
        "vectors": {
            "size": 512,  # FaceNet embedding size
            "distance": "Cosine"  # Best for face recognition
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
    
    # Create the collection
    print(f"📦 Creating collection '{collection}'...")
    response = requests.put(
        f"{base_url}/collections/{collection}",
        json=collection_config
    )
    
    if response.status_code == 200:
        print(f"✅ Successfully created collection '{collection}'")
        
        # Create payload indexes for faster filtering
        print("\n📊 Creating payload indexes...")
        
        # Person ID index
        index_config = {
            "field_name": "person_id",
            "field_type": "keyword"
        }
        idx_response = requests.put(
            f"{base_url}/collections/{collection}/index",
            json=index_config
        )
        if idx_response.status_code == 200:
            print("   ✅ person_id index created")
        
        # Drone ID index
        index_config = {
            "field_name": "drone_id",
            "field_type": "integer"
        }
        idx_response = requests.put(
            f"{base_url}/collections/{collection}/index",
            json=index_config
        )
        if idx_response.status_code == 200:
            print("   ✅ drone_id index created")
        
        # Timestamp index
        index_config = {
            "field_name": "timestamp",
            "field_type": "datetime"
        }
        idx_response = requests.put(
            f"{base_url}/collections/{collection}/index",
            json=index_config
        )
        if idx_response.status_code == 200:
            print("   ✅ timestamp index created")
        
        print("\n🎉 Collection ready to use!")
        return True
    else:
        print(f"❌ Failed to create collection: {response.text}")
        return False

if __name__ == "__main__":
    success = create_drone_collection()
    if not success:
        sys.exit(1)