"""
Distributed LLM for swarm intelligence
"""
import logging
import time
import numpy as np
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import requests

logger = logging.getLogger(__name__)

# Try to import transformer libraries
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("Transformers not available. Using mock LLM.")
    TRANSFORMERS_AVAILABLE = False

class LLMMode(Enum):
    FULL = "full"        # Full 13B model on base
    EDGE = "edge"        # 2.7B model on drones
    TINY = "tiny"        # 1.1B model for emergency
    MOCK = "mock"        # Mock for simulation
    OLLAMA = "ollama"    # Local Ollama instance

class DistributedLLM:
    """
    Distributed LLM that can run on drone swarm
    """
    
    def __init__(self, drone_id: int, swarm_size: int, config: Dict):
        self.drone_id = drone_id
        self.swarm_size = swarm_size
        self.config = config
        self.mode = LLMMode(config.get("llm_mode", "mock"))
        
        # Ollama config
        self.ollama_url = config.get("ollama_url", "http://localhost:11434/api/generate")
        self.ollama_model = config.get("ollama_model", "qwen")
        
        # Model references
        self.model = None
        self.tokenizer = None
        
        # For distributed inference
        self.is_primary = False
        self.model_shard = None
        self.shard_id = None
        
        # Command history
        self.command_history = []
        self.max_history = 100
        
        # Load model based on mode
        if self.mode == LLMMode.OLLAMA:
            logger.info(f"Drone {drone_id}: Using Ollama with model {self.ollama_model}")
        elif self.mode != LLMMode.MOCK and TRANSFORMERS_AVAILABLE:
            self._load_model()
        else:
            logger.info(f"Drone {drone_id}: Using mock LLM")
    
    def _load_model(self):
        """
        Load appropriate model based on mode
        """
        try:
            if self.mode == LLMMode.EDGE:
                model_name = self.config.get("edge_model", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
                logger.info(f"Drone {self.drone_id}: Loading edge model {model_name}")
                
                # 4-bit quantization for edge devices
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16
                )
                
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    quantization_config=bnb_config,
                    device_map="auto",
                    trust_remote_code=True
                )
                
            elif self.mode == LLMMode.TINY:
                model_name = self.config.get("tiny_model", "microsoft/phi-2")
                logger.info(f"Drone {self.drone_id}: Loading tiny model {model_name}")
                
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    device_map="auto",
                    trust_remote_code=True
                )
            
            logger.info(f"✅ Drone {self.drone_id}: LLM loaded ({self._get_model_size():.1f}B params)")
            
        except Exception as e:
            logger.error(f"❌ Failed to load LLM: {e}")
            self.mode = LLMMode.MOCK
    
    def _get_model_size(self) -> float:
        """Get model size in billions of parameters"""
        if self.model:
            return sum(p.numel() for p in self.model.parameters()) / 1e9
        return 0
    
    def interpret_command(self, command: str, context: Dict = None) -> Dict:
        """
        Interpret natural language command
        """
        # Add to history
        self.command_history.append({
            'time': time.time(),
            'command': command,
            'context': context
        })
        
        if self.mode == LLMMode.MOCK:
            # Mock interpretation for simulation
            return self._mock_interpret(command, context)
        elif self.mode == LLMMode.OLLAMA:
            # Ollama interpretation
            return self._ollama_interpret(command, context)
        else:
            # Real LLM interpretation
            return self._llm_interpret(command, context)
            
    def _ollama_interpret(self, command: str, context: Dict = None) -> Dict:
        """
        Interpretation using local Ollama instance
        """
        try:
            system_prompt = """You are a drone swarm command interpreter. 
            Convert natural language commands into structured actions.
            Available actions: takeoff, land, follow, scan, return_home, status, goto, stop.
            Return ONLY a JSON object with 'action', 'params' (dict), and 'confidence' (float).
            Example: {"action": "takeoff", "params": {"altitude": 20}, "confidence": 0.95}"""
            
            prompt = f"{system_prompt}\n\nCommand: {command}\n\nResponse:"
            
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json().get("response", "{}")
                # Clean up response if it has markdown or extra text
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                return json.loads(result)
            else:
                logger.error(f"Ollama error: {response.status_code} - {response.text}")
                return self._mock_interpret(command, context)
                
        except Exception as e:
            logger.error(f"Ollama interpretation failed: {e}")
            return self._mock_interpret(command, context)
    
    def _mock_interpret(self, command: str, context: Dict = None) -> Dict:
        """
        Mock interpretation for simulation
        """
        command = command.lower()
        
        # Parse common commands
        if "takeoff" in command or "launch" in command:
            return {
                'action': 'takeoff',
                'params': {'altitude': 10},
                'confidence': 0.95
            }
        elif "land" in command:
            return {
                'action': 'land',
                'params': {},
                'confidence': 0.95
            }
        elif "follow" in command:
            # Extract target
            words = command.split()
            if "person" in words:
                idx = words.index("person")
                if idx + 1 < len(words) and words[idx+1].isdigit():
                    person_id = f"P{words[idx+1]}"
                else:
                    person_id = "latest"
            else:
                person_id = "latest"
            
            return {
                'action': 'follow',
                'params': {'target': person_id},
                'confidence': 0.85
            }
        elif "scan" in command:
            area = "current"
            if "field" in command:
                area = "field"
            elif "area" in command:
                area = "area"
            
            return {
                'action': 'scan',
                'params': {'area': area, 'duration': 60},
                'confidence': 0.9
            }
        elif "return" in command or "home" in command:
            return {
                'action': 'return_home',
                'params': {},
                'confidence': 0.95
            }
        elif "status" in command:
            return {
                'action': 'status',
                'params': {},
                'confidence': 0.99
            }
        else:
            return {
                'action': 'unknown',
                'params': {'text': command},
                'confidence': 0.5
            }
    
    def _llm_interpret(self, command: str, context: Dict = None) -> Dict:
        """
        Real LLM interpretation
        """
        if not self.model or not self.tokenizer:
            return self._mock_interpret(command, context)
        
        try:
            # Prepare prompt
            system_prompt = """You are a drone swarm command interpreter. 
            Convert natural language commands into structured actions.
            Available actions: takeoff, land, follow, scan, return_home, status, goto, stop.
            Respond with JSON only."""
            
            prompt = f"{system_prompt}\n\nCommand: {command}\n\nResponse:"
            
            # Tokenize
            inputs = self.tokenizer(prompt, return_tensors="pt")
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs.input_ids,
                    max_new_tokens=100,
                    temperature=0.1,
                    do_sample=False
                )
            
            # Decode
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return self._mock_interpret(command, context)
                
        except Exception as e:
            logger.error(f"LLM interpretation failed: {e}")
            return self._mock_interpret(command, context)
    
    def validate_decision(self, decision: Dict, drone_state: Dict) -> bool:
        """
        Validate if a decision is safe/appropriate
        """
        # Check basic safety constraints
        if decision.get('action') == 'goto':
            target = decision.get('params', {}).get('position')
            if target:
                # Check altitude limit
                if target[2] > self.config.get('max_altitude', 120):
                    logger.warning(f"Decision rejected: altitude too high")
                    return False
                
                # Check distance from other drones
                # (would need swarm state)
                pass
        
        elif decision.get('action') == 'follow':
            # Check battery for follow mission
            if drone_state.get('battery', 100) < 30:
                logger.warning(f"Decision rejected: battery too low")
                return False
        
        return True
    
    def distribute_inference(self, command: str, swarm_state: List[Dict]) -> Dict:
        """
        Distributed inference across swarm (when no base)
        """
        if self.is_primary:
            # Primary drone splits command and coordinates
            return self._coordinate_distributed(command, swarm_state)
        else:
            # Secondary drone processes its shard
            return self._process_shard(command)
    
    def _coordinate_distributed(self, command: str, swarm_state: List[Dict]) -> Dict:
        """
        Coordinate distributed inference as primary
        """
        # Split command into parts
        parts = self._split_command(command, self.swarm_size)
        
        # Distribute to other drones
        results = []
        for i, part in enumerate(parts):
            if i == self.drone_id:
                # Process our part
                result = self._process_shard(part)
            else:
                # Would send to other drone via comms
                # For simulation, just mock
                result = {'part': i, 'interpretation': self._mock_interpret(part)}
            results.append(result)
        
        # Aggregate results
        return self._aggregate_results(results)
    
    def _process_shard(self, text: str) -> Dict:
        """
        Process a shard of the command
        """
        return self._mock_interpret(text)
    
    def _split_command(self, command: str, num_parts: int) -> List[str]:
        """
        Split command into parts for distributed processing
        """
        words = command.split()
        part_size = len(words) // num_parts
        
        parts = []
        for i in range(num_parts):
            start = i * part_size
            end = (i + 1) * part_size if i < num_parts - 1 else len(words)
            parts.append(' '.join(words[start:end]))
        
        return parts
    
    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """
        Aggregate distributed inference results
        """
        # Simple majority voting
        actions = [r.get('interpretation', {}).get('action') for r in results]
        
        from collections import Counter
        most_common = Counter(actions).most_common(1)
        
        if most_common:
            action = most_common[0][0]
            # Find first result with this action
            for r in results:
                if r.get('interpretation', {}).get('action') == action:
                    return r['interpretation']
        
        return results[0]['interpretation']
