"""
3D visualization for drone swarm
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from mpl_toolkits.mplot3d import Axes3D
import time
from typing import List, Dict, Optional, Any

class SwarmVisualizer:
    """
    Real-time 3D visualization of drone swarm
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.fig = None
        self.ax = None
        self.drone_plots = []
        self.trajectories = {}
        self.paused = False
        
        # Colors for different drone states
        self.colors = {
            'idle': 'blue',
            'flying': 'green',
            'following': 'red',
            'returning': 'orange',
            'emergency': 'black',
            'manual': 'purple'
        }
        
        # Initialize
        self._init_figure()
        
    def _init_figure(self):
        """Initialize matplotlib figure"""
        self.fig = plt.figure(figsize=(14, 8))
        
        # 3D view
        self.ax = self.fig.add_subplot(121, projection='3d')
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Z (m)')
        self.ax.set_title('Drone Swarm 3D View')
        
        # 2D top view
        self.ax2 = self.fig.add_subplot(122)
        self.ax2.set_xlabel('X (m)')
        self.ax2.set_ylabel('Y (m)')
        self.ax2.set_title('Top View with Heatmap')
        self.ax2.set_aspect('equal')
        
        # Set limits
        world_size = self.config.get("world_size", [1000, 1000])
        self.ax.set_xlim(0, world_size[0])
        self.ax.set_ylim(0, world_size[1])
        self.ax.set_zlim(0, 120)
        
        self.ax2.set_xlim(0, world_size[0])
        self.ax2.set_ylim(0, world_size[1])
        
        # Info text
        self.info_text = self.fig.text(
            0.02, 0.98, '',
            transform=self.fig.transFigure,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        )
        
        plt.ion()
        plt.show()
    
    def update(self, drones: List, knowledge_base=None):
        """Update visualization"""
        if self.paused:
            plt.pause(0.1)
            return
        
        # Clear previous plots
        self.ax.clear()
        self.ax2.clear()
        
        # Reset labels
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Z (m)')
        self.ax.set_title('Drone Swarm 3D View')
        
        self.ax2.set_xlabel('X (m)')
        self.ax2.set_ylabel('Y (m)')
        self.ax2.set_title('Top View with Heatmap')
        
        # Set limits
        world_size = self.config.get("world_size", [1000, 1000])
        self.ax.set_xlim(0, world_size[0])
        self.ax.set_ylim(0, world_size[1])
        self.ax.set_zlim(0, 120)
        
        self.ax2.set_xlim(0, world_size[0])
        self.ax2.set_ylim(0, world_size[1])
        
        # Plot drones
        for drone in drones:
            state = drone.get_state()
            pos = state['pos']
            
            # Choose color based on state
            color = self.colors.get(state['state'], 'blue')
            
            # Plot in 3D
            self.ax.scatter(pos[0], pos[1], pos[2], 
                          c=color, s=100, marker='o')
            
            # Add drone ID
            self.ax.text(pos[0], pos[1], pos[2] + 5, 
                        f"D{drone.id}", fontsize=8)
            
            # Plot in 2D
            self.ax2.scatter(pos[0], pos[1], c=color, s=50)
            self.ax2.text(pos[0], pos[1] + 5, f"D{drone.id}", fontsize=8)
            
            # Show target if following
            if state['state'] == 'following' and state['target']:
                target = state['target']
                self.ax.plot([pos[0], target[0]], 
                           [pos[1], target[1]], 
                           [pos[2], target[2]], 
                           'r--', alpha=0.3)
        
        # Plot heatmap if available
        if knowledge_base:
            hotspots = knowledge_base.get_hotspots(threshold=5)
            if hotspots:
                hs = np.array(hotspots)
                self.ax2.scatter(hs[:, 0], hs[:, 1], 
                               c='red', s=20, alpha=0.5, marker='x')
        
        # Update info text
        info_str = f"Time: {time.time():.1f}\n"
        info_str += f"Drones: {len(drones)}\n"
        info_str += f"Modes: {[d.mode.value for d in drones]}\n"
        info_str += f"States: {[d.state.value for d in drones]}"
        
        self.info_text.set_text(info_str)
        
        plt.pause(0.1)
    
    def pause(self):
        """Pause visualization"""
        self.paused = not self.paused
    
    def close(self):
        """Close visualization"""
        plt.ioff()
        plt.close()