import math
from blockchain import Blockchain, validators

def get_total_attack_probability(node):
    """
    计算节点的总攻击概率
    基于多个检测指标的加权平均
    """
    # 简化的权重系统
    weights = {
        "hash_rate_deviation": 0.3,
        "fork_frequency": 0.2,
        "double_spending": 0.3,
        "voting_power_manipulation": 0.2,
    }
    
    total_probability = 0.0
    
    # Hash Rate Deviation (基于节点历史表现)
    total_probability += weights["hash_rate_deviation"] * check_hash_rate_deviation(node)
    
    # Fork Frequency (基于节点创建的分叉数量)
    total_probability += weights["fork_frequency"] * min(getattr(node, 'forks', 0) / 10.0, 1.0)
    
    # Double Spending (基于双花检测)
    if hasattr(node, 'double_spend_attempts') and node.double_spend_attempts > 0:
        total_probability += weights["double_spending"]
    
    # Voting Power Manipulation (基于质押比例)
    total_probability += weights["voting_power_manipulation"] * check_voting_power_manipulation(node)
    
    # 归一化概率值 (0-1)
    return min(max(total_probability, 0), 1)

def check_hash_rate_deviation(node):
    """检查节点算力偏差"""
    if not hasattr(node, 'hash_rate') or not hasattr(node, 'average_hash_rate'):
        return 0.0
    
    if node.average_hash_rate == 0:
        return 0.0
    
    deviation = abs(node.hash_rate - node.average_hash_rate) / node.average_hash_rate
    return min(deviation, 1.0)

def check_voting_power_manipulation(node):
    """检查投票权操控"""
    if not validators or not hasattr(node, 'address'):
        return 0.0
    
    total_stake = sum(validators.values())
    if total_stake == 0:
        return 0.0
    
    node_stake = validators.get(node.address, 0)
    stake_ratio = node_stake / total_stake
    
    # 如果单个节点控制超过30%的质押，认为存在操控风险
    if stake_ratio > 0.3:
        return stake_ratio
    
    return 0.0

def detect_malicious_behavior(node):
    """
    综合检测恶意行为
    返回检测结果和风险等级
    """
    probability = get_total_attack_probability(node)
    
    if probability > 0.7:
        risk_level = "HIGH"
    elif probability > 0.4:
        risk_level = "MEDIUM"
    elif probability > 0.2:
        risk_level = "LOW"
    else:
        risk_level = "SAFE"
    
    return {
        "probability": probability,
        "risk_level": risk_level,
        "details": {
            "hash_rate_deviation": check_hash_rate_deviation(node),
            "voting_power_ratio": check_voting_power_manipulation(node),
            "fork_count": getattr(node, 'forks', 0),
            "double_spend_attempts": getattr(node, 'double_spend_attempts', 0)
        }
    }
