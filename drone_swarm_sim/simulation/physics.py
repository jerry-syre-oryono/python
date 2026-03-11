import numpy as np
from typing import List, Tuple, Dict, Optional

class PhysicsEngine:
    """
    Simulates physical environment, obstacles, and signal propagation
    """
    
    def __init__(self, world_size: Tuple[int, int]):
        self.world_size = world_size
        self.obstacles = []
        self.jammers = []
        
    def add_obstacle(self, position: List[float], radius: float):
        """Add a spherical obstacle"""
        self.obstacles.append({
            'pos': np.array(position),
            'radius': radius
        })
        
    def add_jammer(self, position: List[float], radius: float, strength: float):
        """Add a signal jammer"""
        self.jammers.append({
            'pos': np.array(position),
            'radius': radius,
            'strength': strength
        })
        
    def get_signal_strength(self, pos1: np.ndarray, pos2: np.ndarray) -> float:
        """
        Calculate signal strength between two points (0.0 to 1.0)
        Considers distance and jamming
        """
        dist = np.linalg.norm(pos1 - pos2)
        
        # Base signal falls off with distance (max range ~1000m)
        max_range = 1000.0
        signal = max(0.0, 1.0 - (dist / max_range)**2)
        
        # Apply jamming
        for jammer in self.jammers:
            j_dist = np.linalg.norm(pos1 - jammer['pos'])
            if j_dist < jammer['radius']:
                # Jamming strength increases closer to jammer center
                jamming_factor = jammer['strength'] * (1.0 - j_dist / jammer['radius'])
                signal -= jamming_factor
                
        # Check line-of-sight obstacles
        for obs in self.obstacles:
            # Simple check: is obstacle close to the line segment between pos1 and pos2?
            # This is a simplified approximation
            obs_dist = self._point_to_segment_dist(obs['pos'], pos1, pos2)
            if obs_dist < obs['radius']:
                signal *= 0.2  # Heavy attenuation through obstacles
                
        return max(0.0, min(1.0, signal))
    
    def check_collision(self, pos1: np.ndarray, pos2: np.ndarray, radius: float = 0.5) -> bool:
        """Check if two drones are colliding"""
        dist = np.linalg.norm(pos1 - pos2)
        return dist < (radius * 2)
        
    def check_obstacle_collision(self, pos: np.ndarray, radius: float = 0.5) -> bool:
        """Check if drone is colliding with any static obstacle"""
        for obs in self.obstacles:
            dist = np.linalg.norm(pos - obs['pos'])
            if dist < (obs['radius'] + radius):
                return True
        return False

    def _point_to_segment_dist(self, p: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate distance from point p to line segment ab"""
        # Vector from a to b
        ab = b - a
        # Vector from a to p
        ap = p - a
        
        # Project ap onto ab to find closest point on infinite line
        t = np.dot(ap, ab) / np.dot(ab, ab)
        
        # Clamp t to segment [0, 1]
        t = max(0.0, min(1.0, t))
        
        # Closest point on segment
        closest = a + t * ab
        
        return np.linalg.norm(p - closest)
