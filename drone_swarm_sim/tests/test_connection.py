#!/usr/bin/env python
"""
Simple test to verify connection to your Qdrant container
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.qdrant_client import DroneQdrantClient
import numpy as np

def test_connection():
    """Test connection to your existing Qdrant"""
    
    print("🔍 Testing Qdrant Connection")
    print("=" * 40)
    
    # Connect to your existing container
    try:
        client = DroneQdrantClient(
            host="localhost",
            port=6333,
            collection="drone_swarm_faces"
        )
        print("✅ Successfully connected to Qdrant!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    # Get statistics
    stats = client.get_statistics()
    print(f"\n📊 Collection Statistics:")
    print(f"   Vectors: {stats.get('vectors_count', 0)}")
    print(f"   Status: {stats.get('status', 'unknown')}")
    
    # Try adding a test face
    print("\n🧪 Testing face insertion...")
    test_embedding = np.random.randn(512).tolist()
    success = client.add_face(
        face_id="test_face_001",
        embedding=test_embedding,
        person_id="TEST001",
        name="Test Person",
        drone_id=0
    )
    
    if success:
        print("✅ Successfully added test face")
        
        # Try searching for it
        results = client.search_face(test_embedding, threshold=0.5)
        if results:
            print(f"✅ Found test face with score: {results[0]['score']:.3f}")
        else:
            print("❌ Could not find test face")
    else:
        print("❌ Failed to add test face")
    
    return True

if __name__ == "__main__":
    success = test_connection()
    if not success:
        sys.exit(1)