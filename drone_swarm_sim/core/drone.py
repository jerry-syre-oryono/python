"""
Base drone class with movement and sensing capabilities
"""
import numpy as np
import time
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class DroneState(Enum):
    IDLE = "idle"
    TAKEOFF = "takeoff"
    FLYING = "flying"
    LANDING = "landing"
    FOLLOWING = "following"
    SCANNING = "scanning"
    RETURNING = "returning"
    EMERGENCY = "emergency"
    MANUAL = "manual"

class DroneMode(Enum):
    BASE = "base"          # Connected to base station
    SWARM = "swarm"        # Swarm mode (no base)
    EMERGENCY = "emergency" # Emergency autonomous mode

class SimulatedDrone:
    """
    Simulated drone with physics and basic capabilities
    """
    
    def __init__(self, drone_id: int, start_pos: List[float], config: Dict):
        self.id = drone_id
        self.config = config
        
        # Position and movement
        self.pos = np.array(start_pos, dtype=float)
        self.velocity = np.zeros(3)
        self.acceleration = np.zeros(3)
        self.yaw = 0.0
        self.target_pos = None
        
        # State
        self.state = DroneState.IDLE
        self.mode = DroneMode.BASE
        self.battery = 100.0
        self.armed = False
        
        # Physics parameters
        self.max_speed = config.get("max_speed", 10.0)  # m/s
        self.max_accel = config.get("max_accel", 3.0)   # m/s²
        self.max_altitude = config.get("max_altitude", 120)  # meters
        self.battery_drain_rate = config.get("battery_drain_rate", 0.1)  # % per second
        
        # Sensors
        self.gps_position = self.pos.copy()
        self.gps_accuracy = 1.0  # meters
        self.has_camera = config.get("has_camera", True)
        
        # Communication
        self.comms = {
            'base': config.get('base_ip', 'localhost'),
            'port': config.get('comms_port', 8080 + drone_id),
            'connected': True,
            'last_heartbeat': time.time()
        }
        
        # Logging
        self.log = []
        self.start_time = time.time()
        
        logger.info(f"🚁 Drone {self.id} initialized at {start_pos}")
    
    def update(self, dt: float = 0.1):
        """
        Update drone state
        """
        # Update battery
        self.battery -= self.battery_drain_rate * dt
        if self.battery <= 0:
            self.emergency_land()
        
        # Update physics
        self._update_physics(dt)
        
        # Update GPS (simulated noise)
        self._update_gps()
        
        # Check for emergency conditions
        self._check_emergency()
        
        # Log state
        if int(time.time() * 10) % 10 == 0:  # Log every 10 updates
            self._log_state()
    
    def _update_physics(self, dt: float):
        """
        Update position based on physics
        """
        if self.target_pos is not None:
            # Calculate desired velocity
            direction = self.target_pos - self.pos
            distance = np.linalg.norm(direction)
            
            if distance < 0.2:
                # Close enough to target
                self.velocity *= 0.1
                if distance < 0.05:
                    self.target_pos = None
                    if self.state == DroneState.TAKEOFF:
                        self.state = DroneState.FLYING
                    elif self.state == DroneState.LANDING:
                        self.state = DroneState.IDLE
            else:
                # Move towards target
                desired_vel = direction / distance * self.max_speed
                
                # If very close, slow down
                if distance < 2.0:
                    desired_vel *= (distance / 2.0)
                
                # Calculate acceleration
                accel = (desired_vel - self.velocity) / dt
                accel_mag = np.linalg.norm(accel)
                if accel_mag > self.max_accel:
                    accel = accel / accel_mag * self.max_accel
                
                self.acceleration = accel
                self.velocity += accel * dt
                
                # Speed limit
                if np.linalg.norm(self.velocity) > self.max_speed:
                    self.velocity = self.velocity / np.linalg.norm(self.velocity) * self.max_speed
        else:
            # No target, slow down
            self.velocity *= 0.9
            if np.linalg.norm(self.velocity) < 0.01:
                self.velocity *= 0
        
        # Keep within bounds
        world_size = self.config.get("world_size", [1000, 1000])
        self.pos[0] = np.clip(self.pos[0], 0, world_size[0])
        self.pos[1] = np.clip(self.pos[1], 0, world_size[1])
        self.pos[2] = np.clip(self.pos[2], 0, self.max_altitude)
    
    def _update_gps(self):
        """
        Simulate GPS with noise
        """
        noise = np.random.normal(0, self.gps_accuracy * 0.1, 3)
        self.gps_position = self.pos + noise
    
    def _check_emergency(self):
        """
        Check for emergency conditions
        """
        if self.battery < 15.0:
            self.emergency_land()
        
        if self.pos[2] > self.max_altitude:
            self.emergency_land()
    
    def _log_state(self):
        """
        Log current state
        """
        self.log.append({
            'time': time.time() - self.start_time,
            'pos': self.pos.copy(),
            'state': self.state.value,
            'battery': self.battery,
            'mode': self.mode.value
        })
        
        # Keep log size manageable
        if len(self.log) > 1000:
            self.log = self.log[-1000:]
    
    # Command methods
    def arm(self):
        """Arm motors"""
        if self.battery > 20:
            self.armed = True
            logger.info(f"Drone {self.id}: Armed")
            return True
        return False
    
    def disarm(self):
        """Disarm motors"""
        self.armed = False
        logger.info(f"Drone {self.id}: Disarmed")
    
    def takeoff(self, altitude: float = 10):
        """Take off to specified altitude"""
        if self.armed:
            self.state = DroneState.TAKEOFF
            self.target_pos = np.array([self.pos[0], self.pos[1], altitude])
            logger.info(f"Drone {self.id}: Taking off to {altitude}m")
            return True
        return False
    
    def land(self):
        """Land at current position"""
        self.state = DroneState.LANDING
        self.target_pos = np.array([self.pos[0], self.pos[1], 0.1])
        logger.info(f"Drone {self.id}: Landing")
    
    def goto(self, x: float, y: float, z: float):
        """Go to specific coordinates"""
        self.target_pos = np.array([x, y, z])
        self.state = DroneState.FLYING
        logger.debug(f"Drone {self.id}: Going to ({x:.1f}, {y:.1f}, {z:.1f})")
    
    def return_to_home(self):
        """Return to home position"""
        home = self.config.get("home_position", [0, 0, 10])
        self.goto(home[0], home[1], home[2])
        self.state = DroneState.RETURNING
        logger.info(f"Drone {self.id}: Returning home")
    
    def emergency_land(self):
        """Emergency landing procedure"""
        self.state = DroneState.EMERGENCY
        self.mode = DroneMode.EMERGENCY
        self.target_pos = np.array([self.pos[0], self.pos[1], 0])
        logger.warning(f"🚨 Drone {self.id}: Emergency landing!")
    
    # Getters
    def get_state(self) -> Dict:
        """Get current state for telemetry"""
        return {
            'id': self.id,
            'pos': self.pos.tolist(),
            'gps': self.gps_position.tolist(),
            'vel': self.velocity.tolist(),
            'yaw': self.yaw,
            'state': self.state.value,
            'mode': self.mode.value,
            'battery': self.battery,
            'armed': self.armed,
            'target': self.target_pos.tolist() if self.target_pos is not None else None,
            'time': time.time() - self.start_time
        }
    
    def get_log(self) -> List[Dict]:
        """Get flight log"""
        return self.log