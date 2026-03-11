"""
Collective knowledge base for drone swarm
"""
import time
import numpy as np
from typing import Dict, List, Optional, Any
from collections import defaultdict
import threading

class CollectiveKnowledge:
    """
    Shared knowledge base for all drones
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.drones = {}
        self.detections = []
        self.heatmap = np.zeros(config.get("world_size", [100, 100]))
        self.people = {}  # person_id -> info
        
        # Locks for thread safety
        self.lock = threading.Lock()
        
        # Decay settings
        self.decay_time = config.get("knowledge_decay", 30.0)
        
        # Start cleanup thread
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
    def update_drone(self, drone_id: int, state: Dict):
        """Update drone position and state"""
        with self.lock:
            self.drones[drone_id] = {
                'state': state,
                'last_seen': time.time()
            }
    
    def add_detection(self, detection: Dict):
        """Add object detection to knowledge base"""
        with self.lock:
            detection['timestamp'] = time.time()
            self.detections.append(detection)
            
            # Update heatmap
            if 'position' in detection:
                pos = detection['position']
                x, y = int(pos[0]), int(pos[1])
                if 0 <= x < self.heatmap.shape[0] and 0 <= y < self.heatmap.shape[1]:
                    self.heatmap[x, y] += 1
            
            # Update people tracking
            if detection.get('class') == 'person' and 'person_id' in detection:
                person_id = detection['person_id']
                
                if person_id not in self.people:
                    self.people[person_id] = {
                        'first_seen': time.time(),
                        'name': detection.get('name', f"Person-{person_id[:6]}"),
                        'sightings': []
                    }
                
                self.people[person_id]['sightings'].append({
                    'time': time.time(),
                    'position': detection.get('position'),
                    'drone_id': detection.get('drone_id')
                })
                self.people[person_id]['last_seen'] = time.time()
    
    def query_area(self, center: List[float], radius: float, 
                   class_filter: Optional[str] = None) -> List[Dict]:
        """Query detections in an area"""
        with self.lock:
            results = []
            center_np = np.array(center)
            
            for d in self.detections:
                # Check age
                if time.time() - d['timestamp'] > self.decay_time:
                    continue
                
                # Check class filter
                if class_filter and d.get('class') != class_filter:
                    continue
                
                # Check distance
                if 'position' in d:
                    dist = np.linalg.norm(np.array(d['position']) - center_np)
                    if dist <= radius:
                        results.append(d)
            
            return results
    
    def get_person_location(self, person_id: str) -> Optional[List[float]]:
        """Get last known location of a person"""
        with self.lock:
            if person_id in self.people:
                sightings = self.people[person_id]['sightings']
                if sightings:
                    return sightings[-1]['position']
        return None
    
    def get_hotspots(self, threshold: float = 3.0) -> List[tuple]:
        """Get areas with many detections"""
        with self.lock:
            hotspots = np.where(self.heatmap > threshold)
            return list(zip(hotspots[0], hotspots[1]))
    
    def get_swarm_status(self) -> Dict:
        """Get overall swarm status"""
        with self.lock:
            return {
                'active_drones': len([d for d in self.drones.values() 
                                     if time.time() - d['last_seen'] < 10]),
                'total_detections': len(self.detections),
                'known_people': len(self.people),
                'heatmap_max': np.max(self.heatmap)
            }
    
    def _cleanup_loop(self):
        """Remove old detections"""
        while self.running:
            time.sleep(5)
            with self.lock:
                # Remove old detections
                current_time = time.time()
                self.detections = [d for d in self.detections 
                                  if current_time - d['timestamp'] <= self.decay_time]
                
                # Decay heatmap
                self.heatmap *= 0.95
    
    def stop(self):
        """Stop cleanup thread"""
        self.running = False