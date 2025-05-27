import random
import time
import threading
import json
from blockchain import mutex, temp_blocks, Blockchain, validators, announcements
from malicious_detection import get_total_attack_probability

# pickWinner creates a lottery pool of validators and chooses the validator who gets to forge a block to the blockchain
def pick_winner():
    time.sleep(3)  # 3 seconds
    with mutex:
        temp = temp_blocks.copy()
    
    lottery_pool = []
    if len(temp) > 0:
        # slightly modified traditional proof of stake algorithm
        # from all validators who submitted a block, weight them by the number of staked tokens
        # in traditional proof of stake, validators can participate without submitting a block to be forged
        for block in temp:
            # if already in lottery pool, skip
            if block.validator in lottery_pool:
                continue
                
            # lock list of validators to prevent data race
            with mutex:
                set_validators = validators.copy()
            
            if block.validator in set_validators:
                k = set_validators[block.validator]
                for i in range(k):
                    lottery_pool.append(block.validator)
        
        # randomly pick winner from lottery pool
        if lottery_pool:
            lottery_winner = elect_validator(lottery_pool)
            
            # add block of winner to blockchain and let all the other nodes know
            for block in temp:
                if block.validator == lottery_winner:
                    with mutex:
                        Blockchain.append(block)
                    
                    # 通知所有节点有新区块被确认
                    for _ in validators:
                        announcements.append(json.dumps({
                            "type": "BLOCK_CONFIRMED",
                            "validator": lottery_winner,
                            "block": {
                                "index": block.index,
                                "timestamp": block.timestamp,
                                "mileage": block.mileage,
                                "hash": block.hash,
                                "validator": block.validator
                            }
                        }))
                    break
    
    with mutex:
        temp_blocks.clear()

def elect_validator(agents):
    # Simple random election for the basic version
    return random.choice(agents) if agents else None

class Agent:
    def __init__(self, address, stake, attack_age=0):
        self.address = address
        self.stake = stake
        self.attack_age = attack_age

def elect_validator_advanced(agents):
    if not agents or len(agents) < 2:
        return agents[0] if agents else None
    
    elected_agents = []
    
    for agent in agents:
        attack_probability = get_total_attack_probability(agent)
        last_attack_attempt = agent.attack_age
        
        if attack_probability * float(last_attack_attempt) >= 2.0:
            agent.attack_age -= 1
            continue
            
        temp_score = -1 * attack_probability * float(last_attack_attempt) * agent.stake
        elected_agents.append((agent, temp_score))
        
        if agent.attack_age > 0:
            agent.attack_age -= 1
    
    # Sort by agent score
    elected_agents.sort(key=lambda x: x[1])
    
    if elected_agents and len(elected_agents) >= 2:
        if elected_agents[0][0].stake == elected_agents[1][0].stake:
            eq_agents = []
            
            for agent, _ in elected_agents:
                if agent.stake == elected_agents[0][0].stake:
                    eq_agents.append(agent)
            
            rand_index = random.randint(0, len(eq_agents) - 1)
            return eq_agents[rand_index]
    
    return elected_agents[0][0] if elected_agents else None
