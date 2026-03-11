"""
Federated learning across drone swarm
"""
import numpy as np
import time
import logging
from typing import Dict, List, Any
import pickle

logger = logging.getLogger(__name__)

class SwarmFederation:
    """
    Federated learning for swarm intelligence
    """
    
    def __init__(self, drone_id: int, config: Dict):
        self.drone_id = drone_id
        self.config = config
        self.local_model = None
        self.global_model = None
        self.training_round = 0
        
        # Training data
        self.training_samples = []
        self.max_samples = config.get("max_training_samples", 1000)
        
        # Federation parameters
        self.min_clients = config.get("min_clients", 3)
        self.round_interval = config.get("round_interval", 300)  # 5 minutes
        self.last_round = time.time()
        
    def add_training_sample(self, sample: Dict):
        """Add a training sample from this drone"""
        self.training_samples.append(sample)
        
        # Keep only recent samples
        if len(self.training_samples) > self.max_samples:
            self.training_samples = self.training_samples[-self.max_samples:]
    
    def train_local(self) -> Dict:
        """Train local model on this drone's data"""
        if not self.training_samples:
            return None
        
        # Mock training for simulation
        # In reality, would fine-tune a model on local data
        
        model_weights = {
            'num_samples': len(self.training_samples),
            'timestamp': time.time(),
            'drone_id': self.drone_id,
            'weights': self._extract_features()
        }
        
        logger.info(f"Drone {self.drone_id}: Local training on {len(self.training_samples)} samples")
        return model_weights
    
    def _extract_features(self) -> Dict:
        """Extract features from training samples"""
        # Mock feature extraction
        return {
            'avg_confidence': np.mean([s.get('confidence', 0.5) for s in self.training_samples]),
            'class_distribution': self._get_class_distribution(),
            'embedding_clusters': np.random.randn(10, 64).tolist()  # Mock embeddings
        }
    
    def _get_class_distribution(self) -> Dict:
        """Get distribution of detected classes"""
        classes = {}
        for sample in self.training_samples:
            cls = sample.get('class', 'unknown')
            classes[cls] = classes.get(cls, 0) + 1
        return classes
    
    def aggregate_models(self, client_models: List[Dict]) -> Dict:
        """
        Aggregate client models using FedAvg
        """
        if not client_models:
            return None
        
        # Weight by number of samples
        total_samples = sum(m['num_samples'] for m in client_models)
        
        # Aggregate (mock implementation)
        aggregated = {
            'round': self.training_round,
            'timestamp': time.time(),
            'num_clients': len(client_models),
            'total_samples': total_samples,
            'global_weights': {
                'avg_confidence': np.average([m['weights']['avg_confidence'] 
                                            for m in client_models],
                                           weights=[m['num_samples'] for m in client_models]),
                'class_distribution': self._merge_class_distributions(client_models)
            }
        }
        
        logger.info(f"✅ Aggregated models from {len(client_models)} clients")
        return aggregated
    
    def _merge_class_distributions(self, client_models: List[Dict]) -> Dict:
        """Merge class distributions from multiple clients"""
        merged = {}
        total_samples = sum(m['num_samples'] for m in client_models)
        
        for model in client_models:
            for cls, count in model['weights']['class_distribution'].items():
                merged[cls] = merged.get(cls, 0) + count
        
        return merged
    
    def should_start_round(self) -> bool:
        """Check if it's time for a new training round"""
        return time.time() - self.last_round > self.round_interval
    
    def start_federation_round(self, all_drones: List[int]) -> bool:
        """
        Start a federated learning round
        """
        if len(all_drones) < self.min_clients:
            logger.warning(f"Not enough drones for federation: {len(all_drones)} < {self.min_clients}")
            return False
        
        logger.info(f"🚀 Starting federation round {self.training_round + 1}")
        
        # Collect local models from all drones
        local_models = []
        for drone_id in all_drones:
            # In real implementation, would request from each drone
            # Here we just mock
            if drone_id == self.drone_id:
                model = self.train_local()
                if model:
                    local_models.append(model)
        
        # Aggregate
        if local_models:
            global_model = self.aggregate_models(local_models)
            self.global_model = global_model
            self.training_round += 1
            self.last_round = time.time()
            
            # Distribute global model (would broadcast to all drones)
            return True
        
        return False