"""
Raft consensus algorithm for drone swarm
"""
import time
import logging
import threading
import random
from enum import Enum
from typing import Dict, List, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

class NodeState(Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"

class ConsensusMessage:
    def __init__(self, msg_type: str, sender: int, term: int, data: Any = None):
        self.type = msg_type
        self.sender = sender
        self.term = term
        self.data = data
        self.timestamp = time.time()

class RaftConsensus:
    """
    Raft consensus implementation for drone swarm
    """
    
    def __init__(self, drone_id: int, all_drones: List[int], config: Dict):
        self.drone_id = drone_id
        self.all_drones = all_drones
        self.config = config
        
        # Raft state
        self.state = NodeState.FOLLOWER
        self.current_term = 0
        self.voted_for = None
        self.leader_id = None
        self.votes_granted = {} # Term -> Set of drone IDs
        
        # Log
        self.log = []  # List of (term, command)
        self.commit_index = -1
        self.last_applied = -1
        
        # Leader state (reinitialized on election)
        self.next_index = {}
        self.match_index = {}
        
        # Timing
        self.heartbeat_interval = config.get("heartbeat_interval", 1.0)
        self.election_timeout_min = config.get("election_timeout_min", 3.0)
        self.election_timeout_max = config.get("election_timeout_max", 5.0)
        self.last_heartbeat = time.time()
        self.last_heartbeat_sent = 0
        self.election_timeout = self._random_timeout()
        
        # Message queues
        self.inbox = []
        self.outbox = defaultdict(list)
        
        # Threading
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info(f"Drone {drone_id}: Raft consensus initialized")
    
    def _random_timeout(self) -> float:
        """Generate random election timeout"""
        return random.uniform(self.election_timeout_min, self.election_timeout_max)
    
    def _run(self):
        """Main consensus loop"""
        while self.running:
            time.sleep(0.1)
            
            with self.lock:
                if self.state == NodeState.LEADER:
                    if time.time() - self.last_heartbeat_sent > self.heartbeat_interval:
                        self._send_heartbeats()
                        self.last_heartbeat_sent = time.time()
                else:
                    self._check_timeout()
                
                self._process_messages()
    
    def _check_timeout(self):
        """Check for election timeout"""
        if self.state != NodeState.LEADER:
            if time.time() - self.last_heartbeat > self.election_timeout:
                self._start_election()
    
    def _start_election(self):
        """Start leader election"""
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.drone_id
        self.votes_granted[self.current_term] = {self.drone_id}
        self.election_timeout = self._random_timeout()
        self.last_heartbeat = time.time() # Reset timer for this term
        
        logger.info(f"Drone {self.drone_id}: Starting election for term {self.current_term}")
        
        # Request votes from all drones
        for drone_id in self.all_drones:
            if drone_id != self.drone_id:
                self._send_message(drone_id, "request_vote", {
                    "term": self.current_term,
                    "candidate_id": self.drone_id,
                    "last_log_index": len(self.log) - 1,
                    "last_log_term": self.log[-1][0] if self.log else -1
                })
    
    def _process_messages(self):
        """Process incoming messages"""
        while self.inbox:
            msg = self.inbox.pop(0)
            
            # If we see a higher term, immediately step down
            if msg.term > self.current_term:
                self.current_term = msg.term
                self.state = NodeState.FOLLOWER
                self.voted_for = None
            
            if msg.type == "request_vote":
                self._handle_vote_request(msg)
            elif msg.type == "vote_response":
                self._handle_vote_response(msg)
            elif msg.type == "append_entries":
                self._handle_append_entries(msg)
            elif msg.type == "append_entries_response":
                self._handle_append_entries_response(msg)
    
    def _handle_vote_request(self, msg: ConsensusMessage):
        """Handle vote request from candidate"""
        # Check if we can vote
        # Check log up-to-date
        last_log_term = self.log[-1][0] if self.log else -1
        last_log_index = len(self.log) - 1
        
        log_ok = (msg.data["last_log_term"] > last_log_term or
                    (msg.data["last_log_term"] == last_log_term and
                    msg.data["last_log_index"] >= last_log_index))
        
        if (msg.term == self.current_term and
            (self.voted_for is None or self.voted_for == msg.sender) and
            log_ok):
            
            self.voted_for = msg.sender
            self.last_heartbeat = time.time()
            
            # Send vote
            self._send_message(msg.sender, "vote_response", {
                "term": self.current_term,
                "vote_granted": True
            })
            
            logger.info(f"Drone {self.drone_id}: Voted for {msg.sender} in term {msg.term}")
        else:
            # Send negative vote
            self._send_message(msg.sender, "vote_response", {
                "term": self.current_term,
                "vote_granted": False
            })
    
    def _handle_vote_response(self, msg: ConsensusMessage):
        """Handle vote response"""
        if self.state != NodeState.CANDIDATE or msg.term != self.current_term:
            return
        
        if msg.data["vote_granted"]:
            # Count votes
            self.votes_granted[self.current_term].add(msg.sender)
            votes = len(self.votes_granted[self.current_term])
            majority = len(self.all_drones) // 2 + 1
            
            if votes >= majority:
                self._become_leader()
    
    def _become_leader(self):
        """Transition to leader state"""
        self.state = NodeState.LEADER
        self.leader_id = self.drone_id
        
        # Initialize leader state
        for drone_id in self.all_drones:
            if drone_id != self.drone_id:
                self.next_index[drone_id] = len(self.log)
                self.match_index[drone_id] = -1
        
        logger.info(f"👑 Drone {self.drone_id} became leader for term {self.current_term}")
        
        # Send initial heartbeats
        self._send_heartbeats()
    
    def _send_heartbeats(self):
        """Send heartbeats to all followers"""
        if self.state != NodeState.LEADER:
            return
        
        for drone_id in self.all_drones:
            if drone_id != self.drone_id:
                self._send_append_entries(drone_id)
        
        self.last_heartbeat = time.time()
    
    def _send_append_entries(self, drone_id: int):
        """Send append entries RPC"""
        prev_log_index = self.next_index[drone_id] - 1
        prev_log_term = self.log[prev_log_index][0] if prev_log_index >= 0 else -1
        
        entries = self.log[self.next_index[drone_id]:] if self.next_index[drone_id] < len(self.log) else []
        
        self._send_message(drone_id, "append_entries", {
            "term": self.current_term,
            "leader_id": self.drone_id,
            "prev_log_index": prev_log_index,
            "prev_log_term": prev_log_term,
            "entries": entries,
            "leader_commit": self.commit_index
        })
    
    def _handle_append_entries(self, msg: ConsensusMessage):
        """Handle append entries RPC"""
        with self.lock:
            if msg.term < self.current_term:
                self._send_message(msg.sender, "append_entries_response", {
                    "term": self.current_term,
                    "success": False,
                    "match_index": -1
                })
                return
            
            if msg.term > self.current_term:
                self.current_term = msg.term
                self.state = NodeState.FOLLOWER
                self.voted_for = None
            
            self.leader_id = msg.sender
            self.last_heartbeat = time.time()
            
            # Check log
            if msg.data["prev_log_index"] >= len(self.log):
                self._send_message(msg.sender, "append_entries_response", {
                    "term": self.current_term,
                    "success": False,
                    "match_index": len(self.log) - 1
                })
                return
            
            # Append entries
            if msg.data["entries"]:
                self.log = self.log[:msg.data["prev_log_index"] + 1]
                self.log.extend(msg.data["entries"])
            
            # Update commit index
            if msg.data["leader_commit"] > self.commit_index:
                self.commit_index = min(msg.data["leader_commit"], len(self.log) - 1)
            
            self._send_message(msg.sender, "append_entries_response", {
                "term": self.current_term,
                "success": True,
                "match_index": len(self.log) - 1
            })
    
    def _handle_append_entries_response(self, msg: ConsensusMessage):
        """Handle append entries response"""
        if self.state != NodeState.LEADER:
            return
        
        if msg.data["success"]:
            # Update match index
            self.match_index[msg.sender] = msg.data["match_index"]
            self.next_index[msg.sender] = msg.data["match_index"] + 1
            
            # Check for majority commit
            for n in range(self.commit_index + 1, len(self.log)):
                count = 1  # Self
                for drone_id in self.all_drones:
                    if drone_id != self.drone_id:
                        if self.match_index.get(drone_id, -1) >= n:
                            count += 1
                
                if count > len(self.all_drones) // 2:
                    self.commit_index = n
        else:
            # Decrement next index and retry
            self.next_index[msg.sender] = max(0, self.next_index[msg.sender] - 1)
            self._send_append_entries(msg.sender)
    
    def _send_message(self, to_drone: int, msg_type: str, data: Any):
        """Send message to another drone"""
        msg = ConsensusMessage(msg_type, self.drone_id, self.current_term, data)
        self.outbox[to_drone].append(msg)
    
    def receive_message(self, msg: ConsensusMessage):
        """Receive message from another drone"""
        self.inbox.append(msg)
    
    def propose_command(self, command: Any) -> bool:
        """Propose a command to the cluster"""
        if self.state != NodeState.LEADER:
            return False
        
        # Append to log
        self.log.append((self.current_term, command))
        
        # Replicate to followers
        for drone_id in self.all_drones:
            if drone_id != self.drone_id:
                self._send_append_entries(drone_id)
        
        return True
    
    def get_leader(self) -> Optional[int]:
        """Get current leader ID"""
        return self.leader_id
    
    def stop(self):
        """Stop consensus thread"""
        self.running = False
        self.thread.join(timeout=1.0)