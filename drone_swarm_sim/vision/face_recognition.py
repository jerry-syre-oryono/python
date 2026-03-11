"""
Face recognition module with Qdrant backend
"""
import cv2
import numpy as np
import time
import logging
from typing import List, Dict, Optional, Tuple
import hashlib
from .qdrant_client import DroneQdrantClient

logger = logging.getLogger(__name__)

# Try to import face recognition libraries
try:
    import torch
    from facenet_pytorch import MTCNN, InceptionResnetV1
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    logger.warning("Face recognition libraries not available. Using simulation mode.")
    FACE_RECOGNITION_AVAILABLE = False

class FaceRecognitionSystem:
    """
    Face recognition system using Qdrant for storage
    """
    
    def __init__(self, qdrant_client: DroneQdrantClient, config: Dict):
        self.qdrant = qdrant_client
        self.config = config
        self.drone_id = config.get("drone_id", 0)
        
        # Initialize face detection models if available
        if FACE_RECOGNITION_AVAILABLE:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.detector = MTCNN(keep_all=True, device=self.device)
            self.encoder = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
            logger.info(f"✅ Face recognition models loaded on {self.device}")
        else:
            self.detector = None
            self.encoder = None
        
        # Cache for recent recognitions (to avoid repeated queries)
        self.cache = {}
        self.cache_ttl = 5  # seconds
        self.cache_max_size = 100
        
        # Recognition threshold
        self.similarity_threshold = config.get("face_similarity_threshold", 0.75)
        
        logger.info("👁️ Face recognition system initialized")
    
    def detect_faces(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect faces in frame and return bounding boxes
        """
        if frame is None:
            return []
        
        if FACE_RECOGNITION_AVAILABLE and self.detector:
            # Real detection
            boxes, probs = self.detector.detect(frame, landmarks=False)
            
            faces = []
            if boxes is not None:
                for i, (box, prob) in enumerate(zip(boxes, probs)):
                    if prob > 0.9:  # Confidence threshold
                        x1, y1, x2, y2 = [int(b) for b in box]
                        
                        # Clamp to frame boundaries
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
                        
                        if x2 > x1 and y2 > y1:
                            face_crop = frame[y1:y2, x1:x2]
                            if face_crop.size > 0:
                                # Generate face ID from image hash
                                face_hash = hashlib.md5(face_crop.tobytes()).hexdigest()[:8]
                                
                                faces.append({
                                    'bbox': [x1, y1, x2, y2],
                                    'confidence': float(prob),
                                    'crop': face_crop,
                                    'face_id': face_hash,
                                    'timestamp': time.time()
                                })
            return faces
        else:
            # Simulation mode
            return self._simulate_detection()
    
    def extract_embedding(self, face_crop: np.ndarray) -> np.ndarray:
        """
        Extract face embedding vector
        """
        if FACE_RECOGNITION_AVAILABLE and self.encoder:
            # Preprocess face for FaceNet
            face_resized = cv2.resize(face_crop, (160, 160))
            face_rgb = cv2.cvtColor(face_resized, cv2.COLOR_BGR2RGB)
            face_normalized = (face_rgb.astype(np.float32) - 127.5) / 128.0
            
            # Convert to tensor
            face_tensor = torch.tensor(face_normalized).permute(2, 0, 1).unsqueeze(0).to(self.device)
            
            # Extract embedding
            with torch.no_grad():
                embedding = self.encoder(face_tensor)
            
            return embedding.cpu().numpy().flatten()
        else:
            # Simulation: deterministic random based on face hash
            face_hash = hashlib.md5(face_crop.tobytes()).digest()
            np.random.seed(int.from_bytes(face_hash[:4], 'little'))
            embedding = np.random.randn(512)
            embedding = embedding / np.linalg.norm(embedding)
            np.random.seed(None)
            return embedding
    
    def recognize_face(self, face_crop: np.ndarray, 
                       location: Optional[List[float]] = None) -> Dict:
        """
        Recognize a face against the database
        """
        # Check cache first (for speed)
        face_hash = hashlib.md5(face_crop.tobytes()).hexdigest()
        
        if face_hash in self.cache:
            cache_entry = self.cache[face_hash]
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                return cache_entry['result']
        
        # Extract embedding
        embedding = self.extract_embedding(face_crop)
        
        # Search in Qdrant
        matches = self.qdrant.search_face(
            embedding.tolist(),
            threshold=self.similarity_threshold
        )
        
        if matches:
            # Known face - return best match
            best_match = matches[0]
            
            # Update last seen in database
            self.qdrant.update_face_seen(
                best_match['id'],
                self.drone_id,
                location
            )
            
            result = {
                'known': True,
                'person_id': best_match['person_id'],
                'name': best_match['name'],
                'similarity': best_match['score'],
                'times_seen': best_match['times_seen'] + 1,
                'embedding': embedding
            }
        else:
            # Unknown face
            result = {
                'known': False,
                'similarity': 0,
                'embedding': embedding,
                'face_hash': face_hash
            }
        
        # Cache result
        self.cache[face_hash] = {
            'timestamp': time.time(),
            'result': result
        }
        
        # Maintain cache size
        if len(self.cache) > self.cache_max_size:
            # Remove oldest entry
            oldest = min(self.cache.keys(), 
                        key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest]
        
        return result
    
    def enroll_face(self, face_crop: np.ndarray, 
                    person_id: str = None,
                    name: str = None,
                    location: List[float] = None) -> str:
        """
        Enroll a new face in the database
        """
        # Generate person ID if not provided
        if person_id is None:
            person_id = f"P{int(time.time())}_{np.random.randint(1000, 9999)}"
        
        # Extract embedding
        embedding = self.extract_embedding(face_crop)
        
        # Generate face ID
        face_id = hashlib.md5(face_crop.tobytes()).hexdigest()[:16]
        
        # Add to Qdrant
        success = self.qdrant.add_face(
            face_id=face_id,
            embedding=embedding.tolist(),
            person_id=person_id,
            name=name,
            drone_id=self.drone_id,
            location=location
        )
        
        if success:
            logger.info(f"✅ Enrolled new face: {name or person_id}")
            return person_id
        else:
            logger.error("❌ Failed to enroll face")
            return None
    
    def _simulate_detection(self) -> List[Dict]:
        """
        Simulate face detection for testing
        """
        # Simulate finding 0-2 faces per frame
        num_faces = np.random.randint(0, 3)
        
        faces = []
        for i in range(num_faces):
            # Create fake face crop
            fake_crop = np.random.randint(0, 255, (160, 160, 3), dtype=np.uint8)
            
            faces.append({
                'bbox': [100 + i*50, 100, 200 + i*50, 200],
                'confidence': 0.95,
                'crop': fake_crop,
                'face_id': f"sim_{i}_{int(time.time())}",
                'timestamp': time.time()
            })
        
        return faces