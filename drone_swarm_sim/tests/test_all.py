#!/usr/bin/env python3
"""
Comprehensive test suite for drone swarm system
"""
import unittest
import sys
import os
import numpy as np
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.drone import SimulatedDrone, DroneState
from core.distributed_llm import DistributedLLM
from core.consensus import RaftConsensus
from vision.qdrant_client import DroneQdrantClient
from swarm.knowledge_base import CollectiveKnowledge

class TestDrone(unittest.TestCase):
    """Test drone functionality"""
    
    def setUp(self):
        self.config = {
            "drone_id": 0,
            "max_speed": 10,
            "max_altitude": 120,
            "world_size": [1000, 1000]
        }
        self.drone = SimulatedDrone(0, [0, 0, 0], self.config)
    
    def test_takeoff(self):
        """Test takeoff command"""
        self.drone.arm()
        self.drone.takeoff(10)
        
        # Update a few times
        for _ in range(20):
            self.drone.update(0.1)
        
        self.assertGreater(self.drone.pos[2], 9)
        self.assertEqual(self.drone.state, DroneState.FLYING)
    
    def test_goto(self):
        """Test goto command"""
        self.drone.arm()
        self.drone.takeoff(10)
        for _ in range(20):
            self.drone.update(0.1)
        
        self.drone.goto(100, 100, 20)
        for _ in range(50):
            self.drone.update(0.1)
        
        # Should have moved towards target
        self.assertGreater(np.linalg.norm(self.drone.pos - [100, 100, 20]), 0)
        self.assertLess(np.linalg.norm(self.drone.pos - [0, 0, 10]), 150)
    
    def test_battery_drain(self):
        """Test battery drain"""
        initial = self.drone.battery
        for _ in range(10):
            self.drone.update(0.1)
        self.assertLess(self.drone.battery, initial)

class TestDistributedLLM(unittest.TestCase):
    """Test distributed LLM"""
    
    def setUp(self):
        self.llm = DistributedLLM(0, 5, {"llm_mode": "mock"})
    
    def test_interpret_command(self):
        """Test command interpretation"""
        result = self.llm.interpret_command("takeoff to 20 meters")
        self.assertEqual(result['action'], 'takeoff')
        
        result = self.llm.interpret_command("follow person 3")
        self.assertEqual(result['action'], 'follow')
    
    def test_validate_decision(self):
        """Test decision validation"""
        decision = {'action': 'goto', 'params': {'position': [0, 0, 200]}}
        state = {'battery': 100}
        
        valid = self.llm.validate_decision(decision, state)
        self.assertFalse(valid)  # Should fail due to altitude

class TestConsensus(unittest.TestCase):
    """Test consensus algorithm"""
    
    def setUp(self):
        self.consensus = RaftConsensus(0, [0, 1, 2], {})
    
    def test_initial_state(self):
        """Test initial state"""
        self.assertEqual(self.consensus.state.value, "follower")
        self.assertEqual(self.consensus.current_term, 0)
    
    def test_leader_election(self):
        """Test leader election"""
        # Trigger election
        self.consensus._start_election()
        
        # Should become candidate
        self.assertEqual(self.consensus.state.value, "candidate")
        self.assertGreater(self.consensus.current_term, 0)

class TestQdrant(unittest.TestCase):
    """Test Qdrant integration"""
    
    @classmethod
    def setUpClass(cls):
        """Check Qdrant connection"""
        try:
            cls.client = DroneQdrantClient()
            cls.connected = True
        except:
            cls.connected = False
    
    def test_connection(self):
        """Test Qdrant connection"""
        if not self.connected:
            self.skipTest("Qdrant not available")
        
        stats = self.client.get_statistics()
        self.assertIsNotNone(stats)
    
    def test_add_and_search(self):
        """Test adding and searching faces"""
        if not self.connected:
            self.skipTest("Qdrant not available")
        
        # Create test embedding
        embedding = np.random.randn(512).tolist()
        
        # Add face
        success = self.client.add_face(
            face_id="test_face",
            embedding=embedding,
            person_id="test_person",
            name="Test User"
        )
        self.assertTrue(success)
        
        # Search for it
        results = self.client.search_face(embedding, threshold=0.5)
        self.assertTrue(len(results) > 0)

class TestKnowledgeBase(unittest.TestCase):
    """Test collective knowledge"""
    
    def setUp(self):
        self.kb = CollectiveKnowledge({"world_size": [100, 100]})
    
    def test_add_detection(self):
        """Test adding detections"""
        detection = {
            'class': 'person',
            'person_id': 'P1',
            'position': [10, 10, 0]
        }
        self.kb.add_detection(detection)
        
        # Query should find it
        results = self.kb.query_area([10, 10], 5)
        self.assertEqual(len(results), 1)
    
    def test_heatmap(self):
        """Test heatmap generation"""
        for i in range(10):
            self.kb.add_detection({
                'class': 'object',
                'position': [i, i, 0]
            })
        
        hotspots = self.kb.get_hotspots(threshold=1)
        self.assertTrue(len(hotspots) > 0)

if __name__ == "__main__":
    unittest.main()