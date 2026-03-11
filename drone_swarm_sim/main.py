#!/usr/bin/env python3
"""
Drone Swarm System with Distributed LLM and Qdrant
Main entry point
"""
import os
import sys
import time
import logging
import threading
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import configuration
from config.settings import Config

# Import core modules
from core.drone import SimulatedDrone, DroneState, DroneMode
from core.distributed_llm import DistributedLLM, LLMMode
from core.consensus import RaftConsensus

# Import vision modules
from vision.qdrant_client import DroneQdrantClient
from vision.face_recognition import FaceRecognitionSystem
from vision.tracker import TargetTracker

# Import swarm modules
from swarm.knowledge_base import CollectiveKnowledge
from swarm.federation import SwarmFederation

# Import simulation
from simulation.physics import PhysicsEngine
from simulation.visualizer import SwarmVisualizer
from simulation.scenarios import TestScenarios

# Setup logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv("LOG_FILE", "swarm.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DroneSwarmSystem:
    """
    Main drone swarm system coordinator
    """
    
    def __init__(self):
        logger.info("🚁 Initializing Drone Swarm System")
        
        # Load configuration
        self.config = Config()
        
        # Initialize components
        self._init_components()
        
        # Start console interface
        self.running = True
        self.console_thread = threading.Thread(target=self._console_loop)
        self.console_thread.daemon = True
        
        # Auto-takeoff for demo
        self._command_takeoff()
        
        logger.info("✅ System initialized")
    
    def _init_components(self):
        """Initialize all system components"""
        
        # Connect to Qdrant
        logger.info("📡 Connecting to Qdrant...")
        self.qdrant = DroneQdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=6333,  # Your existing container port
            collection=os.getenv("QDRANT_COLLECTION", "drone_swarm_faces")
        )
        
        # Initialize physics engine
        self.physics = PhysicsEngine(
            world_size=self.config.WORLD_SIZE
        )
        
        # Initialize knowledge base
        self.knowledge = CollectiveKnowledge(self.config.__dict__)
        
        # Create drones
        self.drones = []
        drone_ids = []
        
        for i in range(self.config.NUM_DRONES):
            # Drone config
            drone_config = {
                "drone_id": i,
                "max_speed": self.config.MAX_SPEED,
                "max_altitude": self.config.MAX_ALTITUDE,
                "world_size": self.config.WORLD_SIZE,
                "home_position": self.config.HOME_POSITION,
                "base_ip": self.config.BASE_STATION_IP
            }
            
            # Create drone
            drone = SimulatedDrone(
                drone_id=i,
                start_pos=self.config.DRONE_START_POSITIONS[i],
                config=drone_config
            )
            
            self.drones.append(drone)
            drone_ids.append(i)
            
            logger.info(f"  Created Drone {i}")
        
        # Initialize face recognition for each drone
        self.face_systems = []
        for i, drone in enumerate(self.drones):
            face_config = {
                "drone_id": i,
                "face_similarity_threshold": self.config.FACE_SIMILARITY_THRESHOLD
            }
            face_system = FaceRecognitionSystem(self.qdrant, face_config)
            self.face_systems.append(face_system)
        
        # Initialize distributed LLM for each drone
        self.llms = []
        for i in range(self.config.NUM_DRONES):
            llm = DistributedLLM(
                drone_id=i,
                swarm_size=self.config.NUM_DRONES,
                config={
                    "llm_mode": self.config.LLM_MODE,
                    "edge_model": self.config.EDGE_MODEL,
                    "tiny_model": self.config.TINY_MODEL,
                    "ollama_url": self.config.OLLAMA_URL,
                    "ollama_model": self.config.OLLAMA_MODEL
                }
            )
            self.llms.append(llm)
        
        # Initialize consensus for each drone
        self.consensus = []
        for i in range(self.config.NUM_DRONES):
            cons = RaftConsensus(
                drone_id=i,
                all_drones=drone_ids,
                config={
                    "heartbeat_interval": self.config.HEARTBEAT_INTERVAL,
                    "election_timeout_min": self.config.ELECTION_TIMEOUT_MIN,
                    "election_timeout_max": self.config.ELECTION_TIMEOUT_MAX
                }
            )
            self.consensus.append(cons)
        
        # Initialize federation
        self.federation = SwarmFederation(
            drone_id=0,
            config=self.config.__dict__
        )
        
        # Initialize visualizer
        self.visualizer = SwarmVisualizer(self.config.__dict__)
        
        # Add test obstacles
        self.physics.add_obstacle([300, 300, 0], 50)
        self.physics.add_obstacle([700, 500, 0], 40)
        
        # Add test jammer
        self.physics.add_jammer([500, 500, 0], 200, strength=0.8)
    
    def _console_loop(self):
        """Interactive console loop"""
        print("\n" + "="*60)
        print("Drone Swarm System Console")
        print("="*60)
        print("Commands:")
        print("  status          - Show swarm status")
        print("  takeoff         - Launch all drones")
        print("  land            - Land all drones")
        print("  scan            - Start area scan")
        print("  follow [id]     - Follow person by ID")
        print("  stop            - Stop current action")
        print("  mode            - Show operation mode")
        print("  pause           - Pause visualization")
        print("  quit            - Exit")
        print("="*60)
        
        while self.running:
            try:
                cmd = input("\n> ").strip().lower()
                
                if cmd == 'quit':
                    self.running = False
                    break
                elif cmd == 'status':
                    self._show_status()
                elif cmd == 'takeoff':
                    self._command_takeoff()
                elif cmd == 'land':
                    self._command_land()
                elif cmd == 'scan':
                    self._command_scan()
                elif cmd.startswith('follow'):
                    parts = cmd.split()
                    if len(parts) > 1:
                        self._command_follow(parts[1])
                    else:
                        print("Please specify person ID")
                elif cmd == 'stop':
                    self._command_stop()
                elif cmd == 'mode':
                    self._show_mode()
                elif cmd == 'pause':
                    self.visualizer.pause()
                    print("Visualization paused" if self.visualizer.paused else "Visualization resumed")
                else:
                    print(f"Unknown command: {cmd}")
                    
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                logger.error(f"Console error: {e}")
    
    def _show_status(self):
        """Show swarm status"""
        print("\n📊 Swarm Status:")
        for drone in self.drones:
            state = drone.get_state()
            mode_str = "🟢" if drone.mode == DroneMode.BASE else "🟡" if drone.mode == DroneMode.SWARM else "🔴"
            print(f"  {mode_str} Drone {drone.id}: {state['state']} "
                  f"at ({state['pos'][0]:.1f}, {state['pos'][1]:.1f}, {state['pos'][2]:.1f}) "
                  f"Batt: {state['battery']:.1f}%")
        
        # Qdrant stats
        stats = self.qdrant.get_statistics()
        print(f"\n🗄️ Qdrant: {stats.get('vectors_count', 0)} faces in database")
        
        # Known people
        people = self.knowledge.people
        print(f"👥 Known people: {len(people)}")
        for pid, info in list(people.items())[:3]:
            print(f"  - {info['name']}: {len(info['sightings'])} sightings")
    
    def _show_mode(self):
        """Show operation mode"""
        # Check if any drone is in swarm mode
        swarm_mode = any(d.mode == DroneMode.SWARM for d in self.drones)
        
        if swarm_mode:
            leader = next((d for d in self.drones if d.id == self.consensus[0].leader_id), None)
            print(f"\n🟡 SWARM MODE - No base station")
            if leader:
                print(f"   Leader: Drone {leader.id}")
        else:
            print(f"\n🟢 BASE MODE - Connected to base station")
    
    def _command_takeoff(self):
        """Command all drones to take off"""
        print("🛫 Taking off all drones")
        for drone in self.drones:
            drone.arm()
            drone.takeoff(altitude=20)
    
    def _command_land(self):
        """Command all drones to land"""
        print("🛬 Landing all drones")
        for drone in self.drones:
            drone.land()
    
    def _command_scan(self):
        """Start area scan"""
        print("🔍 Starting area scan")
        
        # Create scan pattern
        for i, drone in enumerate(self.drones):
            x = 200 + (i * 100)
            y = 200 + (i % 3) * 100
            drone.goto(x, y, 30)
            drone.state = DroneState.SCANNING
    
    def _command_follow(self, person_id: str):
        """Follow a specific person"""
        print(f"👁️ Following person: {person_id}")
        
        # Find person in knowledge base
        if person_id in self.knowledge.people:
            location = self.knowledge.get_person_location(person_id)
            if location:
                # Assign nearest drone
                distances = [np.linalg.norm(drone.pos - np.array(location)) 
                           for drone in self.drones]
                nearest_idx = np.argmin(distances)
                
                self.drones[nearest_idx].goto(
                    location[0], location[1] - 10, location[2] + 15
                )
                self.drones[nearest_idx].state = DroneState.FOLLOWING
                print(f"  Drone {nearest_idx} assigned")
            else:
                print("  No recent location for this person")
        else:
            print(f"  Person {person_id} not found")
    
    def _command_stop(self):
        """Stop current actions"""
        print("🛑 Stopping all drones")
        for drone in self.drones:
            drone.target_pos = None
            if drone.state not in [DroneState.LANDING, DroneState.EMERGENCY]:
                drone.state = DroneState.FLYING
                drone.velocity *= 0
    
    def run(self):
        """Main simulation loop"""
        logger.info("🚀 Starting simulation")
        
        # Start console thread
        self.console_thread.start()
        
        # Simulation parameters
        step = 0
        dt = self.config.SIMULATION_STEP
        
        # Base station position
        base_pos = np.array([0, 0, 0])
        
        try:
            while self.running and step < self.config.MAX_STEPS:
                # Update physics for each drone
                for i, drone in enumerate(self.drones):
                    # Check base station connection
                    signal = self.physics.get_signal_strength(drone.pos, base_pos)
                    
                    if signal < 0.1 and drone.mode == DroneMode.BASE:
                        drone.mode = DroneMode.SWARM
                        logger.warning(f"Drone {drone.id} lost base connection - switching to swarm mode")
                    elif signal > 0.3 and drone.mode == DroneMode.SWARM:
                        drone.mode = DroneMode.BASE
                        logger.info(f"Drone {drone.id} reconnected to base")
                    
                    # Update drone physics
                    # (simplified - just move towards target)
                    drone.update(dt)
                    
                    # Simulate camera and face detection
                    if np.random.random() < 0.05:  # 5% chance per step
                        self._simulate_detection(i, drone.pos)
                    
                    # Update knowledge base
                    self.knowledge.update_drone(drone.id, drone.get_state())
                
                # Consensus message passing
                for i, cons in enumerate(self.consensus):
                    for to_drone_id, messages in list(cons.outbox.items()):
                        while messages:
                            msg = messages.pop(0)
                            if to_drone_id < len(self.consensus):
                                self.consensus[to_drone_id].receive_message(msg)
                
                # Check for collisions
                for i in range(len(self.drones)):
                    for j in range(i+1, len(self.drones)):
                        if self.physics.check_collision(self.drones[i].pos, self.drones[j].pos):
                            logger.warning(f"Collision warning: Drone {i} and Drone {j}")
                
                # Update visualization
                if step % 10 == 0:
                    self.visualizer.update(self.drones, self.knowledge)
                
                # Federation round
                if self.federation.should_start_round():
                    self.federation.start_federation_round(list(range(len(self.drones))))
                
                step += 1
                time.sleep(dt)
                
        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
        finally:
            self.cleanup()
    
    def _simulate_detection(self, drone_idx: int, drone_pos: np.ndarray):
        """Simulate face detection for testing"""
        # Randomly generate person detections
        if np.random.random() < 0.3:
            # Generate person ID
            person_id = f"P{np.random.randint(1, 6)}"
            name = f"Person {person_id[1:]}"
            
            # Position near drone
            offset = np.random.randn(3) * 20
            person_pos = drone_pos + offset
            person_pos[2] = 0  # On ground
            
            # Add to knowledge base
            detection = {
                'class': 'person',
                'person_id': person_id,
                'name': name,
                'position': person_pos.tolist(),
                'confidence': 0.95,
                'drone_id': drone_idx
            }
            
            self.knowledge.add_detection(detection)
            
            # Add to Qdrant if new
            if person_id not in self.knowledge.people:
                # Simulate face crop
                fake_crop = np.random.randint(0, 255, (160, 160, 3), dtype=np.uint8)
                self.face_systems[drone_idx].enroll_face(
                    fake_crop, person_id, name, person_pos.tolist()
                )
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("🧹 Cleaning up...")
        self.running = False
        
        # Land all drones
        for drone in self.drones:
            drone.land()
            drone.disarm()
        
        # Stop consensus
        for cons in self.consensus:
            cons.stop()
        
        # Close visualization
        self.visualizer.close()
        
        logger.info("👋 Simulation ended")

if __name__ == "__main__":
    system = DroneSwarmSystem()
    system.run()
