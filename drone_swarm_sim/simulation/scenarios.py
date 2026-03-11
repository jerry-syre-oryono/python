import numpy as np
from typing import List, Dict

class TestScenarios:
    """
    Predefined test scenarios for drone swarm evaluation
    """
    
    @staticmethod
    def area_search(world_size: List[int], num_drones: int) -> List[np.ndarray]:
        """Generate grid search positions for drones"""
        positions = []
        rows = int(np.sqrt(num_drones))
        cols = (num_drones // rows) + (1 if num_drones % rows > 0 else 0)
        
        dx = world_size[0] / (cols + 1)
        dy = world_size[1] / (rows + 1)
        
        for i in range(num_drones):
            r = i // cols
            c = i % cols
            pos = np.array([dx * (c + 1), dy * (r + 1), 30.0])
            positions.append(pos)
            
        return positions

    @staticmethod
    def boundary_patrol(world_size: List[int], num_drones: int) -> List[np.ndarray]:
        """Generate patrol points along the perimeter"""
        # Simplified perimeter distribution
        points = []
        width, height = world_size[0], world_size[1]
        perimeter = 2 * (width + height)
        segment = perimeter / num_drones
        
        for i in range(num_drones):
            d = i * segment
            if d < width:
                pos = [d, 50, 40]
            elif d < width + height:
                pos = [width - 50, d - width, 40]
            elif d < 2 * width + height:
                pos = [width - (d - (width + height)), height - 50, 40]
            else:
                pos = [50, height - (d - (2 * width + height)), 40]
            points.append(np.array(pos))
            
        return points
