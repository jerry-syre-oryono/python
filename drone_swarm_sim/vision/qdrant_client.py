"""
Qdrant client for face embeddings - using your existing container
"""
import os
import logging
import uuid
from typing import List, Dict, Optional, Any
import numpy as np
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams

logger = logging.getLogger(__name__)

class DroneQdrantClient:
    """
    Client for Qdrant vector database - connects to your existing container
    """
    
    def __init__(self, host: str = "localhost", port: int = 6333, 
                 collection: str = "drone_swarm_faces", api_key: Optional[str] = None):
        """
        Initialize connection to your existing Qdrant container
        
        Args:
            host: Qdrant host (default: localhost)
            port: Qdrant port (default: 6333 - your existing container)
            collection: Collection name for drone swarm (default: drone_swarm_faces)
            api_key: Optional API key if you have authentication enabled
        """
        self.host = host
        self.port = port
        self.collection_name = collection
        self.api_key = api_key
        
        # Connect to your existing Qdrant
        self.client = QdrantClient(host=host, port=port, api_key=api_key)
        
        # Test connection and verify collection
        self._initialize()
        
    def _initialize(self):
        """Test connection and verify collection exists"""
        try:
            # Test connection
            self.client.get_collections()
            logger.info(f"✅ Connected to Qdrant at {self.host}:{self.port}")
            
            # Check if our collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                logger.warning(f"⚠️ Collection '{self.collection_name}' not found")
                logger.info("Please run: python scripts/create_drone_collection.py")
            else:
                # Get collection info
                info = self.client.get_collection(self.collection_name)
                logger.info(f"📊 Collection '{self.collection_name}' has {info.points_count} vectors")
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {e}")
            logger.error("   Make sure your container is running: docker start qdrant")
            raise
    
    def add_face(self, face_id: str, embedding: List[float], 
                 person_id: str, name: str = None, 
                 drone_id: int = None, location: List[float] = None,
                 metadata: Dict = None) -> bool:
        """
        Add a face embedding to the database
        """
        try:
            point_id = str(uuid.uuid4())
            
            payload = {
                "face_id": face_id,
                "person_id": person_id,
                "name": name or f"Person-{person_id[:6]}",
                "drone_id": drone_id,
                "timestamp": datetime.now().isoformat(),
                "location": location,
                "times_seen": 1,
                "last_seen": datetime.now().isoformat()
            }
            
            if metadata:
                payload.update(metadata)
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            
            logger.debug(f"✅ Added face {person_id} to database")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add face: {e}")
            return False
    
    def search_face(self, embedding: List[float], threshold: float = 0.75, limit: int = 5) -> List[Dict]:
        """
        Search for similar faces in the database
        """
        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=embedding,
                limit=limit,
                score_threshold=threshold,
                with_payload=True
            ).points
            
            matches = []
            for result in results:
                matches.append({
                    "id": result.id,
                    "score": result.score,
                    "person_id": result.payload.get("person_id"),
                    "name": result.payload.get("name"),
                    "drone_id": result.payload.get("drone_id"),
                    "timestamp": result.payload.get("timestamp"),
                    "location": result.payload.get("location"),
                    "times_seen": result.payload.get("times_seen", 0)
                })
            
            return matches
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def update_face_seen(self, point_id: str, drone_id: int, location: List[float]) -> bool:
        """
        Update last seen information for a face
        """
        try:
            # Get current point to increment times_seen
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id],
                with_payload=True
            )
            
            if points:
                current = points[0].payload
                times_seen = current.get("times_seen", 0) + 1
                
                self.client.set_payload(
                    collection_name=self.collection_name,
                    payload={
                        "times_seen": times_seen,
                        "last_seen": datetime.now().isoformat(),
                        "last_drone": drone_id,
                        "last_location": location
                    },
                    points=[point_id]
                )
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update face: {e}")
            return False
    
    def get_face_by_person_id(self, person_id: str) -> Optional[Dict]:
        """
        Retrieve a face by person ID
        """
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="person_id",
                            match=models.MatchValue(value=person_id)
                        )
                    ]
                ),
                limit=1
            )
            
            if results[0]:
                point = results[0][0]
                return {
                    "id": point.id,
                    "person_id": point.payload.get("person_id"),
                    "name": point.payload.get("name"),
                    "vector": point.vector,
                    "payload": point.payload
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve face: {e}")
            return None
    
    def get_all_faces(self, limit: int = 100) -> List[Dict]:
        """
        Get all faces (for backup/sync)
        """
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=True
            )
            
            faces = []
            for point in results[0]:
                faces.append({
                    "id": point.id,
                    "vector": point.vector.tolist() if hasattr(point.vector, 'tolist') else point.vector,
                    "payload": point.payload
                })
            
            return faces
            
        except Exception as e:
            logger.error(f"❌ Failed to get faces: {e}")
            return []
    
    def delete_face(self, point_id: str) -> bool:
        """
        Delete a face from database
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[point_id]
                )
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete face: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """
        Get collection statistics
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "vectors_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status,
                "optimizer_status": info.optimizer_status
            }
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {}
    
    def health_check(self) -> bool:
        """
        Check if Qdrant is healthy
        """
        try:
            self.client.get_collections()
            return True
        except:
            return False