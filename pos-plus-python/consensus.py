import random
import time
import threading
import json
from blockchain import mutex, temp_blocks, Blockchain, validators, announcements
from malicious_detection import get_total_attack_probability

# pickWinner 创建一个验证者的抽奖池，并选择一个验证者来将区块添加到区块链中
def pick_winner():
    time.sleep(3)  # 3秒
    with mutex:
        temp = temp_blocks.copy()
    
    lottery_pool = []
    if len(temp) > 0:
        # 略微修改的传统权益证明算法
        # 从所有提交区块的验证者中，根据其质押代币数量加权
        # 在传统的权益证明中，验证者可以不提交区块也能参与
        for block in temp:
            # 如果已在抽奖池中，跳过
            if block.validator in lottery_pool:
                continue
                
            # 锁定验证者列表以防止数据竞争
            with mutex:
                set_validators = validators.copy()
            
            if block.validator in set_validators:
                k = set_validators[block.validator]
                for i in range(k):
                    lottery_pool.append(block.validator)
        
        # 从抽奖池中随机选出获胜者
        if lottery_pool:
            lottery_winner = elect_validator(lottery_pool)
            
            # 将获胜者的区块添加到区块链，并通知所有其他节点
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

# 基础版本的简单随机选举
def elect_validator(agents):
    # Simple random election for the basic version
    return random.choice(agents) if agents else None

class Agent:
    def __init__(self, address, stake, attack_age=0):
        self.address = address
        self.stake = stake
        self.attack_age = attack_age

# 高级选举算法，考虑攻击概率和攻击年龄
def elect_validator_advanced(agents):
    # Advanced election algorithm considering attack probability and attack age
    if not agents or len(agents) < 2:
        return agents[0] if agents else None
    
    elected_agents = []
    
    for agent in agents:
        attack_probability = get_total_attack_probability(agent)
        last_attack_attempt = agent.attack_age
        
        # 如果攻击概率和攻击年龄的乘积大于等于2，则跳过该代理
        if attack_probability * float(last_attack_attempt) >= 2.0:
            agent.attack_age -= 1
            continue
            
        temp_score = -1 * attack_probability * float(last_attack_attempt) * agent.stake
        elected_agents.append((agent, temp_score))
        
        if agent.attack_age > 0:
            agent.attack_age -= 1
    
    # 按代理得分排序
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
