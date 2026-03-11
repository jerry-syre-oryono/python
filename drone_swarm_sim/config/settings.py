"""
Configuration settings for drone swarm system
"""
import os
import numpy as np

class Config:
    """System configuration"""
    
    # Drone swarm settings
    NUM_DRONES = int(os.getenv("NUM_DRONES", "5"))
    WORLD_SIZE = [1000, 1000]  # meters
    HOME_POSITION = [500, 500, 0]
    
    # Drone start positions
    DRONE_START_POSITIONS = np.array([
        [400, 400, 0],
        [450, 450, 0],
        [500, 500, 0],
        [550, 550, 0],
        [600, 600, 0]
    ])
    
    # Drone capabilities
    MAX_SPEED = 10.0  # m/s
    MAX_ALTITUDE = 120  # meters
    SAFE_DISTANCE = 5.0  # meters between drones
    
    # Base station
    BASE_STATION_IP = os.getenv("BASE_STATION_IP", "192.168.1.100")
    BASE_STATION_PORT = int(os.getenv("BASE_STATION_PORT", "8080"))
    
    # Simulation
    SIMULATION_STEP = 0.1  # seconds
    MAX_STEPS = 10000
    
    # Consensus settings
    HEARTBEAT_INTERVAL = 1.0  # seconds
    ELECTION_TIMEOUT_MIN = 3.0
    ELECTION_TIMEOUT_MAX = 5.0
    
    # LLM settings
    LLM_MODE = os.getenv("LLM_MODE", "mock")  # full, edge, tiny, mock, ollama
    EDGE_MODEL = os.getenv("EDGE_MODEL", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    TINY_MODEL = os.getenv("TINY_MODEL", "microsoft/phi-2")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen")
    
    # Face recognition
    FACE_SIMILARITY_THRESHOLD = 0.75
    EMBEDDING_SIZE = 512
    
    # Knowledge base
    KNOWLEDGE_DECAY = 30.0  # seconds
    
    # Federation
    FEDERATION_ROUND_INTERVAL = 300  # seconds
    MIN_CLIENTS_FOR_FEDERATION = 3
    MAX_TRAINING_SAMPLES = 1000
    
    def __init__(self):
        # Convert string lists to actual lists
        if isinstance(self.WORLD_SIZE, str):
            self.WORLD_SIZE = [float(x) for x in self.WORLD_SIZE.split(',')]