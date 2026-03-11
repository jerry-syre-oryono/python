import numpy as np
import time
from typing import List, Dict, Optional

class TargetTracker:
    """
    Keeps track of detected targets across frames using simple position estimation
    """
    
    def __init__(self):
        self.active_targets = {}
        self.target_count = 0
        self.max_lost_time = 2.0  # seconds
        
    def update(self, detections: List[Dict]):
        """Update existing targets or create new ones from new detections"""
        current_time = time.time()
        
        # Mark all current targets as potentially lost
        for target_id in list(self.active_targets.keys()):
            # If target hasn't been seen for too long, remove it
            if current_time - self.active_targets[target_id]['last_seen'] > self.max_lost_time:
                del self.active_targets[target_id]
        
        # Match detections to active targets
        for det in detections:
            matched = False
            det_pos = np.array(det['position'])
            
            # Simple Euclidean distance matching
            for target_id, target in self.active_targets.items():
                target_pos = np.array(target['position'])
                dist = np.linalg.norm(det_pos - target_pos)
                
                if dist < 50.0:  # Threshold for matching
                    # Update target
                    target['position'] = det_pos.tolist()
                    target['last_seen'] = current_time
                    target['confidence'] = det.get('confidence', 0.9)
                    matched = True
                    break
            
            if not matched:
                # Create new target
                new_id = f"T{self.target_count:03d}"
                self.active_targets[new_id] = {
                    'id': new_id,
                    'position': det_pos.tolist(),
                    'last_seen': current_time,
                    'confidence': det.get('confidence', 0.9),
                    'class': det.get('class', 'unknown')
                }
                self.target_count += 1
                
        return self.active_targets
