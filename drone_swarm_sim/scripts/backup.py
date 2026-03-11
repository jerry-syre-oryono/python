#!/usr/bin/env python3
"""
Backup Qdrant face database
"""
import sys
import os
import json
import time
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.qdrant_client import DroneQdrantClient

def backup_faces():
    """Backup all faces from Qdrant"""
    
    # Connect to Qdrant
    client = DroneQdrantClient()
    
    print("📦 Backing up face database...")
    
    # Get all faces
    faces = client.get_all_faces(limit=10000)
    
    if not faces:
        print("No faces found in database")
        return
    
    # Create backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_faces_{timestamp}.json"
    
    # Save to file
    with open(backup_file, 'w') as f:
        json.dump(faces, f, indent=2)
    
    print(f"✅ Backed up {len(faces)} faces to {backup_file}")
    print(f"   File size: {os.path.getsize(backup_file) / 1024:.2f} KB")

def restore_faces(backup_file):
    """Restore faces from backup"""
    
    if not os.path.exists(backup_file):
        print(f"❌ Backup file not found: {backup_file}")
        return
    
    # Connect to Qdrant
    client = DroneQdrantClient()
    
    print(f"♻️ Restoring from {backup_file}...")
    
    # Load backup
    with open(backup_file, 'r') as f:
        faces = json.load(f)
    
    # Restore each face
    success = 0
    for face in faces:
        result = client.add_face(
            face_id=face['payload']['face_id'],
            embedding=face['vector'],
            person_id=face['payload']['person_id'],
            name=face['payload'].get('name'),
            drone_id=face['payload'].get('drone_id'),
            location=face['payload'].get('location'),
            metadata=face['payload']
        )
        if result:
            success += 1
    
    print(f"✅ Restored {success}/{len(faces)} faces")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--restore" and len(sys.argv) > 2:
            restore_faces(sys.argv[2])
        else:
            print("Usage: python backup.py [--restore <backup_file>]")
    else:
        backup_faces()