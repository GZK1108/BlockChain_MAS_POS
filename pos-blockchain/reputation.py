import json
import os

class ValidatorReputationSystem:
    def __init__(self, node_id):
        self.node_id = node_id
        # 五个核心声誉指标
        self.metrics = {
            'accuracy': 1.0,           # 历史验证准确性 (0-1)
            # 'holding_tendency': ,    # 交易持有倾向 (0-1)
            # 'processing_delay': ,    # 处理延迟 (0-1)
            # 'processing_power': ,   # 处理能力 (0-1)
            # 'detection_ability':,    # 非法交易检测能力 (0-1)
        }
        # 强化学习权重
        self.weights = {
            'accuracy': 1.0,
            # 'holding_tendency': 1.0,
            # 'processing_delay': 1.0,
            # 'processing_power': 1.0,
            # 'detection_ability': 1.0
        }
        # 学习参数
        self.learning_rate = 0.1
        self.discount_factor = 0.9
    
    def calculate_vote_score(self, block):
        """计算区块的声誉得分，用于投票决策"""
        score = 0
        score += self.weights['accuracy'] * self.metrics['accuracy']
        return score
    
    def decide_vote(self, block):
        """决定投票投不投票，看是否超过阈值"""
        vote_score = self.calculate_vote_score(block)
        # 决策阈值（动态调整）
        threshold = 0.7 
        return "ACCEPT" if vote_score >= threshold else "REJECT"
    
    def update_from_vote_result(self, block, vote_decision, was_correct):
        """根据投票结果更新声誉系统（强化学习）"""
        # 计算奖励
        reward = self.calculate_reward(vote_decision, was_correct)
        
        # 根据奖励更新权重
        for metric in self.weights:
            self.weights[metric] += self.learning_rate * (
                reward + self.discount_factor * self.metrics.get(metric, 1) - self.weights[metric]
            )
            # 限制权重范围
            self.weights[metric] = max(0.1, min(2.0, self.weights[metric]))
        
        # 根据结果更新声誉
        self.update_metrics(block, vote_decision, was_correct)
    
    def calculate_reward(self, vote_decision, was_correct=None):
        #计算奖励
        #correct怎么判断？？？
        if vote_decision == "ACCEPT":
            return 5
        else:  # REJECT
            return -4
    
    def update_metrics(self, block, vote_decision, was_correct=None):
        """根据投票结果更新声誉指标"""
        # 更新准确性
        if vote_decision:
            self.metrics['accuracy'] = min(1.0, self.metrics['accuracy'] + 0.05)
        else:
            self.metrics['accuracy'] = max(0.0, self.metrics['accuracy'] - 0.1)
        
        #  根据区块特征更新其他指标
        
        # 确保所有指标在0-1范围内
        for metric in self.metrics:
            self.metrics[metric] = max(0.0, min(1.0, self.metrics[metric]))
    