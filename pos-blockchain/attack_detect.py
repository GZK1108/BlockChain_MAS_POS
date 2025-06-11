# attack_detect.py - 双花攻击检测模块
# Copyright (c) 2025 GZK
# Peking University - School of Software and Microelectronics
#
# For academic use only. Commercial usage is prohibited without authorization.

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Any, Optional

class DoubleSpendingDetector:
    """双花攻击检测器"""
    
    def __init__(self, detection_window: int = 60, similarity_threshold: float = 0.8):
        """
        初始化双花攻击检测器
        
        Args:
            detection_window: 检测时间窗口（秒）
            similarity_threshold: 相似度阈值，超过此值视为可疑交易
        """
        self.detection_window = detection_window
        self.similarity_threshold = similarity_threshold
        
        # 存储交易和区块历史
        self.node_transactions = defaultdict(list)  # 按节点存储交易
        self.transactions_by_sender = defaultdict(list)  # 按发送者存储交易
        self.recent_blocks = defaultdict(list)  # 按节点存储区块
        self.detected_attacks = []  # 检测到的攻击列表
        
        # 防重复检测
        self.processed_tx_ids = set()  # 已处理的交易ID
        self.detected_pairs = set()    # 已检测的交易对
        
        # 设置日志
        self.logger = logging.getLogger('AttackDetector')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
    def add_transaction(self, node_id: str, transaction_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        添加新交易并检测双花攻击
        
        Args:
            node_id: 发送交易的节点ID
            transaction_data: 交易数据字典
            
        Returns:
            检测到的可疑模式列表
        """
        try:
            # 验证输入数据
            if not isinstance(transaction_data, dict):
                self.logger.error(f"Transaction data is not a dictionary: {type(transaction_data)}")
                return []
            
            # 安全地获取交易数据
            from_address = transaction_data.get('from_address', '')
            to_address = transaction_data.get('to_address', '')
            amount = transaction_data.get('amount', 0)
            tx_id = transaction_data.get('transaction_id', '')
            
            # 验证必需字段
            if not from_address or not to_address or amount <= 0:
                self.logger.debug(f"Invalid transaction data: from={from_address}, to={to_address}, amount={amount}")
                return []
            
            # **关键修复：排除质押交易（自己向自己转账）**
            if from_address == to_address:
                self.logger.info(f"[DETECT] Skipping staking transaction (self-transfer): {from_address} -> {to_address} : {amount}")
                return []
            
            timestamp = datetime.now()
            
            # 生成更唯一的交易ID，避免重复
            if not tx_id:
                tx_id = f"tx_{from_address}_{to_address}_{amount}_{timestamp.timestamp():.6f}"
            
            tx_info = {
                'timestamp': timestamp,
                'node_id': str(node_id),
                'from_address': str(from_address),
                'to_address': str(to_address),
                'amount': float(amount),
                'tx_id': str(tx_id)
            }
            
            self.logger.info(f"[DETECT] Processing transaction: {from_address} -> {to_address} : {amount} (ID: {tx_id[:16]}...)")
            
            # **关键修复1：检查是否是重复交易**
            if self._is_duplicate_transaction(tx_info):
                self.logger.info(f"[DETECT] Duplicate transaction detected, skipping: {tx_id[:16]}...")
                return []
            
            # **关键修复2：检查交易ID是否已处理**
            if tx_id in self.processed_tx_ids:
                self.logger.info(f"[DETECT] Transaction already processed, skipping: {tx_id[:16]}...")
                return []
            
            # 标记为已处理
            self.processed_tx_ids.add(tx_id)
            
            # 获取历史交易进行检测（排除重复）
            historical_txs = self._get_unique_historical_transactions(from_address, tx_info)
            self.logger.info(f"[DETECT] Found {len(historical_txs)} unique historical transactions")
            
            # 先进行双花检测
            patterns = self._detect_double_spending_against_history(tx_info, historical_txs)
            
            # 检测完成后再存储当前交易
            self.node_transactions[node_id].append(tx_info)
            self.transactions_by_sender[from_address].append(tx_info)
            
            # 清理过期数据
            self._cleanup_old_data()
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error in add_transaction: {e}")
            import traceback
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return []
    
    def add_block(self, node_id: str, block_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        添加新区块并检测分叉双花攻击
        
        Args:
            node_id: 发送区块的节点ID
            block_data: 区块数据字典
            
        Returns:
            检测到的可疑模式列表
        """
        try:
            # 验证输入数据
            if not isinstance(block_data, dict):
                self.logger.error(f"Block data is not a dictionary: {type(block_data)}")
                return []
            
            # 安全地获取区块数据
            height = block_data.get('height', 0)
            parent_hash = block_data.get('parent_hash', '')
            block_hash = block_data.get('hash', '')
            transactions = block_data.get('transactions', [])
            
            timestamp = datetime.now()
            block_info = {
                'timestamp': timestamp,
                'node_id': str(node_id),
                'block_height': int(height),
                'parent_hash': str(parent_hash),
                'block_hash': str(block_hash),
                'transactions': list(transactions) if isinstance(transactions, list) else []
            }
            
            self.logger.info(f"[DETECT] Adding block: height={height} from {node_id} with {len(transactions)} transactions")
            
            # 先检测分叉双花
            patterns = self._detect_fork_double_spending(block_info)
            
            # 然后存储区块
            self.recent_blocks[node_id].append(block_info)
            self._cleanup_old_data()
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error in add_block: {e}")
            import traceback
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return []
    
    def _is_duplicate_transaction(self, new_tx: Dict[str, Any]) -> bool:
        """检查是否为重复交易"""
        try:
            from_addr = new_tx.get('from_address', '')
            to_addr = new_tx.get('to_address', '')
            amount = new_tx.get('amount', 0)
            new_time = new_tx.get('timestamp', datetime.now())
            
            # 检查发送者的历史交易
            sender_txs = self.transactions_by_sender.get(from_addr, [])
            
            for tx in sender_txs:
                # 检查是否在很短时间内有完全相同的交易
                if (tx.get('to_address') == to_addr and 
                    tx.get('amount') == amount and
                    abs((new_time - tx.get('timestamp', datetime.min)).total_seconds()) < 2.0):  # 2秒内
                    self.logger.debug(f"[DEDUP] Found duplicate: same tx within 2 seconds")
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking duplicate: {e}")
            return False
    
    def _get_unique_historical_transactions(self, from_address: str, current_tx: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取去重的历史交易，排除质押交易"""
        try:
            all_txs = self.transactions_by_sender.get(from_address, [])
            current_time = current_tx.get('timestamp', datetime.now())
            current_id = current_tx.get('tx_id', '')
            
            unique_txs = []
            seen_signatures = set()
            
            for tx in all_txs:
                try:
                    # 排除当前交易
                    if tx.get('tx_id') == current_id:
                        continue
                    
                    # **排除质押交易（自己向自己转账）**
                    tx_from = tx.get('from_address', '')
                    tx_to = tx.get('to_address', '')
                    if tx_from == tx_to:
                        self.logger.debug(f"[DEDUP] Skipping staking transaction in history: {tx_from} -> {tx_to}")
                        continue
                    
                    # 检查时间窗口
                    time_diff = abs((current_time - tx.get('timestamp', datetime.min)).total_seconds())
                    if time_diff > self.detection_window:
                        continue
                    
                    # 创建交易签名，避免重复（精确到秒）
                    tx_timestamp = tx.get('timestamp', datetime.min)
                    tx_signature = f"{tx_to}_{tx.get('amount')}_{int(tx_timestamp.timestamp())}"
                    
                    if tx_signature not in seen_signatures:
                        seen_signatures.add(tx_signature)
                        unique_txs.append(tx)
                        self.logger.debug(f"[DEDUP] Added unique tx: {tx_signature}")
                    else:
                        self.logger.debug(f"[DEDUP] Skipping duplicate transaction: {tx_signature}")
                        
                except Exception as e:
                    self.logger.debug(f"Error processing transaction: {e}")
                    continue
            
            return unique_txs
            
        except Exception as e:
            self.logger.error(f"Error getting unique transactions: {e}")
            return []
    
    def _detect_double_spending_against_history(self, new_tx: Dict[str, Any], historical_txs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对比新交易与历史交易检测双花 - 防重复版本"""
        try:
            suspicious_patterns = []
            from_addr = new_tx.get('from_address', '')
            new_to = new_tx.get('to_address', '')
            new_amount = new_tx.get('amount', 0)
            new_id = new_tx.get('tx_id', 'unknown')
            
            self.logger.info(f"[DETECT] ===== DOUBLE SPENDING CHECK =====")
            self.logger.info(f"[DETECT] New TX: {from_addr} -> {new_to} : {new_amount} (ID: {new_id[:16]}...)")
            self.logger.info(f"[DETECT] Checking against {len(historical_txs)} historical transactions")
            
            if not historical_txs:
                self.logger.info(f"[DETECT] No historical transactions to compare")
                return []
            
            for i, tx in enumerate(historical_txs):
                try:
                    tx_to = tx.get('to_address', '')
                    tx_amount = tx.get('amount', 0)
                    tx_id = tx.get('tx_id', f'unknown_{i}')
                    
                    # **关键修复3：创建唯一的配对ID，避免重复检测**
                    pair_id = tuple(sorted([new_id, tx_id]))
                    if pair_id in self.detected_pairs:
                        self.logger.debug(f"[DETECT] Skipping already detected pair")
                        continue
                    
                    self.logger.info(f"[DETECT] Comparing: {new_to}({new_amount}) vs {tx_to}({tx_amount})")
                    
                    # 计算相似度
                    similarity = self._calculate_similarity_simple(new_tx, tx)
                    self.logger.info(f"[DETECT] Similarity: {similarity:.3f} (threshold: {self.similarity_threshold})")
                    
                    if similarity >= self.similarity_threshold:
                        # **关键修复4：记录已检测的配对，避免重复**
                        self.detected_pairs.add(pair_id)
                        
                        self.logger.warning(f"[DETECT] *** DOUBLE SPENDING DETECTED! ***")
                        self.logger.warning(f"[DETECT] {from_addr}: {new_to}({new_amount}) vs {tx_to}({tx_amount})")
                        
                        pattern = {
                            'attack_id': f"ds_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.detected_attacks):03d}",
                            'type': 'POTENTIAL_DOUBLE_SPENDING',
                            'confidence': float(similarity),
                            'severity': 'HIGH' if similarity > 0.8 else ('MEDIUM' if similarity > 0.6 else 'LOW'),
                            'description': f"双花检测: {from_addr} 向不同接收方({new_to} vs {tx_to})转账相似金额({new_amount} vs {tx_amount})",
                            'detection_time': datetime.now().isoformat(),
                            'transactions': [
                                {
                                    'tx_id': new_id,
                                    'to': new_to,
                                    'amount': new_amount,
                                    'node': new_tx.get('node_id', 'unknown'),
                                    'time': new_tx.get('timestamp', datetime.now()).isoformat()
                                },
                                {
                                    'tx_id': tx_id,
                                    'to': tx_to,
                                    'amount': tx_amount,
                                    'node': tx.get('node_id', 'unknown'),
                                    'time': tx.get('timestamp', datetime.now()).isoformat()
                                }
                            ]
                        }
                        suspicious_patterns.append(pattern)
                        self.detected_attacks.append(pattern)
                        
                        # 只检测第一个匹配的，避免多重检测
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error comparing transaction {i}: {e}")
                    continue
            
            self.logger.info(f"[DETECT] Detection result: {len(suspicious_patterns)} unique patterns")
            return suspicious_patterns
            
        except Exception as e:
            self.logger.error(f"Error in double spending detection: {e}")
            import traceback
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return []
    
    def _calculate_similarity_simple(self, tx1: Dict[str, Any], tx2: Dict[str, Any]) -> float:
        """
        简化的相似度计算 - 专注于双花特征，排除质押交易
        
        Args:
            tx1: 第一个交易
            tx2: 第二个交易
            
        Returns:
            相似度分数 (0.0 到 1.0)
        """
        try:
            similarity = 0.0
            
            from1 = tx1.get('from_address', '')
            from2 = tx2.get('from_address', '')
            to1 = tx1.get('to_address', '')
            to2 = tx2.get('to_address', '')
            amount1 = float(tx1.get('amount', 0))
            amount2 = float(tx2.get('amount', 0))
            
            self.logger.debug(f"[SIMILARITY] TX1: {from1} -> {to1} : {amount1}")
            self.logger.debug(f"[SIMILARITY] TX2: {from2} -> {to2} : {amount2}")
            
            # **关键修复：排除质押交易（自己向自己转账）**
            if from1 == to1:
                self.logger.debug(f"[SIMILARITY] TX1 is staking (self-transfer), not double spending")
                return 0.0
            
            if from2 == to2:
                self.logger.debug(f"[SIMILARITY] TX2 is staking (self-transfer), not double spending")
                return 0.0
            
            # 1. 相同发送者 (必要条件) +50%
            if from1 == from2 and from1:
                similarity += 0.5
                self.logger.debug(f"[SIMILARITY] Same sender: +0.5 -> {similarity}")
            else:
                self.logger.debug(f"[SIMILARITY] Different senders, not double spending")
                return 0.0
            
            # 2. 不同接收者 (双花关键特征) +20%
            if to1 != to2 and to1 and to2:
                similarity += 0.2
                self.logger.debug(f"[SIMILARITY] Different recipients: +0.2 -> {similarity}")
            elif to1 == to2:
                # 相同接收者可能是重复交易，给少量分数
                similarity += 0.1
                self.logger.debug(f"[SIMILARITY] Same recipient (duplicate?): +0.1 -> {similarity}")
            
            # 3. 金额相等或相近 +30%
            if amount1 > 0 and amount2 > 0:
                if amount1 == amount2:
                    similarity += 0.3
                    self.logger.debug(f"[SIMILARITY] Exact same amount: +0.3 -> {similarity}")
                else:
                    # 计算金额差异百分比
                    amount_diff = abs(amount1 - amount2) / max(amount1, amount2)
                    if amount_diff <= 0.1:  # 10%以内视为相似
                        amount_score = 0.3 * (1 - amount_diff / 0.1)
                        similarity += amount_score
                        self.logger.debug(f"[SIMILARITY] Similar amount (diff: {amount_diff:.1%}): +{amount_score:.3f} -> {similarity}")
            
            final_similarity = min(similarity, 1.0)
            self.logger.info(f"[SIMILARITY] Final similarity: {final_similarity:.3f}")
            
            return final_similarity
            
        except Exception as e:
            self.logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def _detect_fork_double_spending(self, new_block: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        检测分叉中的双花攻击
        
        Args:
            new_block: 新区块信息
            
        Returns:
            检测到的可疑模式列表
        """
        try:
            suspicious_patterns = []
            new_height = new_block.get('block_height', 0)
            new_hash = new_block.get('block_hash', '')
            
            if not new_hash:
                return []
            
            self.logger.info(f"[DETECT] Checking for fork double spending at height {new_height}")
            
            # 检查同高度不同区块
            same_height_blocks = []
            for node_id, block_list in self.recent_blocks.items():
                for block in block_list:
                    try:
                        if (block.get('block_height') == new_height and
                            block.get('block_hash') != new_hash and
                            block.get('node_id') != new_block.get('node_id')):
                            same_height_blocks.append(block)
                            self.logger.info(f"[DETECT] Found competing block at height {new_height} from {block.get('node_id')}")
                    except Exception as e:
                        self.logger.debug(f"Error processing block: {e}")
                        continue
            
            if same_height_blocks:
                self.logger.info(f"[DETECT] Found {len(same_height_blocks)} competing blocks at height {new_height}")
                
                for fork_block in same_height_blocks:
                    try:
                        conflicts = self._find_transaction_conflicts(
                            new_block.get('transactions', []), 
                            fork_block.get('transactions', [])
                        )
                        
                        if conflicts:
                            pattern = {
                                'attack_id': f"fork_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.detected_attacks)}",
                                'type': 'FORK_DOUBLE_SPENDING',
                                'confidence': 0.95,
                                'severity': 'CRITICAL',
                                'description': f"分叉双花: 高度 {new_height} 存在冲突交易",
                                'detection_time': datetime.now().isoformat(),
                                'fork_info': {
                                    'height': new_height,
                                    'conflicts': len(conflicts),
                                    'block1_node': new_block.get('node_id', 'unknown'),
                                    'block2_node': fork_block.get('node_id', 'unknown'),
                                    'block1_hash': new_block.get('block_hash', 'unknown')[:16] + '...',
                                    'block2_hash': fork_block.get('block_hash', 'unknown')[:16] + '...'
                                },
                                'conflicts_detail': conflicts
                            }
                            suspicious_patterns.append(pattern)
                            self.detected_attacks.append(pattern)
                            self.logger.warning(f"[DETECT] *** FORK DOUBLE SPENDING DETECTED! *** {len(conflicts)} conflicts at height {new_height}")
                            
                    except Exception as e:
                        self.logger.debug(f"Error processing fork: {e}")
                        continue
            
            return suspicious_patterns
            
        except Exception as e:
            self.logger.error(f"Error in _detect_fork_double_spending: {e}")
            import traceback
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return []
    
    def _find_transaction_conflicts(self, txs1: List[Dict], txs2: List[Dict]) -> List[Dict]:
        """
        查找两个交易列表中的冲突交易，排除质押交易
        
        Args:
            txs1: 第一个交易列表
            txs2: 第二个交易列表
            
        Returns:
            冲突交易信息列表
        """
        try:
            conflicts = []
            
            for tx1 in txs1:
                for tx2 in txs2:
                    try:
                        from1 = tx1.get('from_address', '') if isinstance(tx1, dict) else ''
                        from2 = tx2.get('from_address', '') if isinstance(tx2, dict) else ''
                        to1 = tx1.get('to_address', '') if isinstance(tx1, dict) else ''
                        to2 = tx2.get('to_address', '') if isinstance(tx2, dict) else ''
                        amount1 = float(tx1.get('amount', 0)) if isinstance(tx1, dict) else 0
                        amount2 = float(tx2.get('amount', 0)) if isinstance(tx2, dict) else 0
                        
                        # **关键修复：排除质押交易**
                        if from1 == to1 or from2 == to2:
                            self.logger.debug(f"[CONFLICT] Skipping staking transaction in conflict detection")
                            continue
                        
                        # 检测双花：相同发送者，不同接收者，相似金额
                        if (from1 == from2 and from1 and  # 相同发送者
                            to1 != to2 and to1 and to2 and  # 不同接收者
                            abs(amount1 - amount2) <= max(amount1, amount2) * 0.2):  # 相似金额(20%容差)
                            conflicts.append({
                                'from_address': from1,
                                'amount1': amount1,
                                'amount2': amount2,
                                'to1': to1,
                                'to2': to2,
                                'tx1_id': tx1.get('transaction_id', 'unknown'),
                                'tx2_id': tx2.get('transaction_id', 'unknown')
                            })
                            self.logger.info(f"[CONFLICT] Found conflict: {from1} -> {to1}({amount1}) vs {to2}({amount2})")
                            
                    except Exception as e:
                        self.logger.debug(f"Error checking conflict: {e}")
                        continue
                        
            return conflicts
            
        except Exception as e:
            self.logger.error(f"Error finding conflicts: {e}")
            import traceback
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return []
    
    def _cleanup_old_data(self):
        """清理过期数据"""
        try:
            cutoff_time = datetime.now() - timedelta(seconds=self.detection_window)
            
            # 清理按节点分组的交易
            for node_id in list(self.node_transactions.keys()):
                old_count = len(self.node_transactions[node_id])
                self.node_transactions[node_id] = [
                    tx for tx in self.node_transactions[node_id]
                    if tx.get('timestamp', datetime.min) > cutoff_time
                ]
                new_count = len(self.node_transactions[node_id])
                if old_count != new_count:
                    self.logger.debug(f"[CLEANUP] Cleaned {old_count - new_count} old transactions for {node_id}")
                # 清理空列表
                if not self.node_transactions[node_id]:
                    del self.node_transactions[node_id]
            
            # 清理按发送者分组的交易
            for sender in list(self.transactions_by_sender.keys()):
                old_count = len(self.transactions_by_sender[sender])
                self.transactions_by_sender[sender] = [
                    tx for tx in self.transactions_by_sender[sender]
                    if tx.get('timestamp', datetime.min) > cutoff_time
                ]
                new_count = len(self.transactions_by_sender[sender])
                if old_count != new_count:
                    self.logger.debug(f"[CLEANUP] Cleaned {old_count - new_count} old transactions for sender {sender}")
                # 清理空列表
                if not self.transactions_by_sender[sender]:
                    del self.transactions_by_sender[sender]
            
            # 清理区块
            for node_id in list(self.recent_blocks.keys()):
                old_count = len(self.recent_blocks[node_id])
                self.recent_blocks[node_id] = [
                    block for block in self.recent_blocks[node_id]
                    if block.get('timestamp', datetime.min) > cutoff_time
                ]
                new_count = len(self.recent_blocks[node_id])
                if old_count != new_count:
                    self.logger.debug(f"[CLEANUP] Cleaned {old_count - new_count} old blocks for {node_id}")
                # 清理空列表
                if not self.recent_blocks[node_id]:
                    del self.recent_blocks[node_id]
            
            # 清理过期的交易ID记录
            cutoff_timestamp = cutoff_time.timestamp()
            expired_ids = set()
            for tx_id in self.processed_tx_ids:
                try:
                    # 从ID中提取时间戳进行清理
                    if '_' in tx_id:
                        parts = tx_id.split('_')
                        if len(parts) >= 4:
                            timestamp_str = parts[-1]
                            if float(timestamp_str) < cutoff_timestamp:
                                expired_ids.add(tx_id)
                except:
                    # 如果无法解析时间戳，保留ID
                    pass
            
            for tx_id in expired_ids:
                self.processed_tx_ids.discard(tx_id)
            
            if expired_ids:
                self.logger.debug(f"[CLEANUP] Cleaned {len(expired_ids)} expired transaction IDs")
                
        except Exception as e:
            self.logger.error(f"Error cleaning data: {e}")
    
    def get_detection_status(self) -> Dict[str, Any]:
        """
        获取检测器状态信息
        
        Returns:
            状态信息字典
        """
        try:
            return {
                'detection_window': self.detection_window,
                'similarity_threshold': self.similarity_threshold,
                'monitored_nodes': len(self.node_transactions),
                'total_attacks_detected': len(self.detected_attacks),
                'processed_tx_count': len(self.processed_tx_ids),
                'detected_pairs_count': len(self.detected_pairs),
                'recent_transactions': {
                    node_id: len(txs) for node_id, txs in self.node_transactions.items()
                },
                'transactions_by_sender': {
                    sender: len(txs) for sender, txs in self.transactions_by_sender.items()
                },
                'recent_blocks': {
                    node_id: len(blocks) for node_id, blocks in self.recent_blocks.items()
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting status: {e}")
            return {
                'detection_window': self.detection_window,
                'similarity_threshold': self.similarity_threshold,
                'monitored_nodes': 0,
                'total_attacks_detected': 0,
                'processed_tx_count': 0,
                'detected_pairs_count': 0,
                'recent_transactions': {},
                'transactions_by_sender': {},
                'recent_blocks': {}
            }
    
    def get_attack_history(self) -> List[Dict[str, Any]]:
        """
        获取攻击历史记录
        
        Returns:
            攻击记录列表
        """
        try:
            return self.detected_attacks.copy()
        except Exception as e:
            self.logger.error(f"Error getting history: {e}")
            return []
    
    def set_threshold(self, threshold: float) -> bool:
        """
        设置相似度阈值
        
        Args:
            threshold: 新的阈值 (0.0 到 1.0)
            
        Returns:
            设置是否成功
        """
        try:
            threshold = float(threshold)
            if 0.0 <= threshold <= 1.0:
                old_threshold = self.similarity_threshold
                self.similarity_threshold = threshold
                self.logger.info(f"[CONFIG] Threshold changed from {old_threshold} to {threshold}")
                return True
            return False
        except (ValueError, TypeError):
            return False
    
    def clear_attacks(self):
        """清空攻击历史"""
        try:
            old_count = len(self.detected_attacks)
            self.detected_attacks.clear()
            self.detected_pairs.clear()  # 同时清空检测对记录
            self.logger.info(f"[CLEAR] Cleared {old_count} attack records and detection pairs")
        except Exception as e:
            self.logger.error(f"Error clearing attacks: {e}")
    
    def reset_detector(self):
        """重置检测器状态"""
        try:
            self.node_transactions.clear()
            self.transactions_by_sender.clear()
            self.recent_blocks.clear()
            self.detected_attacks.clear()
            self.processed_tx_ids.clear()
            self.detected_pairs.clear()
            self.logger.info("[RESET] Detector state reset")
        except Exception as e:
            self.logger.error(f"Error resetting detector: {e}")


class AttackAlertManager:
    """攻击警报管理器"""
    
    def __init__(self):
        """初始化警报管理器"""
        self.logger = logging.getLogger('AttackAlert')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        self.alert_callbacks = []
        self.sent_alerts = set()  # 防止重复发送警报
    
    def add_alert_callback(self, callback):
        """
        添加警报回调函数
        
        Args:
            callback: 回调函数，接收攻击模式作为参数
        """
        try:
            if callable(callback):
                self.alert_callbacks.append(callback)
                self.logger.info(f"Added alert callback: {callback.__name__}")
        except Exception as e:
            self.logger.error(f"Error adding callback: {e}")
    
    async def send_alert(self, attack_patterns: List[Dict[str, Any]]):
        """
        发送攻击警报
        
        Args:
            attack_patterns: 攻击模式列表
        """
        try:
            if not attack_patterns:
                return
                
            for pattern in attack_patterns:
                attack_id = pattern.get('attack_id', 'unknown')
                
                # 防止重复发送相同的警报
                if attack_id not in self.sent_alerts:
                    self.sent_alerts.add(attack_id)
                    await self._format_and_send_alert(pattern)
                else:
                    self.logger.debug(f"Skipping duplicate alert: {attack_id}")
                
        except Exception as e:
            self.logger.error(f"Error sending alerts: {e}")
    
    async def _format_and_send_alert(self, pattern: Dict[str, Any]):
        """
        格式化并发送单个警报
        
        Args:
            pattern: 攻击模式字典
        """
        try:
            severity_emoji = {
                'LOW': '⚠️',
                'MEDIUM': '🔶',
                'HIGH': '🔴',
                'CRITICAL': '🚨'
            }
            
            emoji = severity_emoji.get(pattern.get('severity', 'MEDIUM'), '⚠️')
            confidence = pattern.get('confidence', 0)
            
            if isinstance(confidence, (int, float)):
                confidence_str = f"{confidence:.2%}"
            else:
                confidence_str = str(confidence)
            
            alert_msg = f"""
{'='*60}
{emoji} 双花攻击检测警报 {emoji}
{'='*60}
攻击ID: {pattern.get('attack_id', 'unknown')}
类型: {pattern.get('type', 'UNKNOWN')}
严重程度: {pattern.get('severity', 'UNKNOWN')}
置信度: {confidence_str}
描述: {pattern.get('description', 'No description')}
检测时间: {pattern.get('detection_time', 'unknown')}
"""
            
            # 添加详细信息
            if pattern.get('type') == 'POTENTIAL_DOUBLE_SPENDING':
                transactions = pattern.get('transactions', [])
                if len(transactions) >= 2:
                    alert_msg += f"""
涉及交易:
  交易1: ID={transactions[0].get('tx_id', 'unknown')[:16]}... | 
         接收方: {transactions[0].get('to', 'unknown')} | 
         金额: {transactions[0].get('amount', 0)} | 
         节点: {transactions[0].get('node', 'unknown')}
  交易2: ID={transactions[1].get('tx_id', 'unknown')[:16]}... | 
         接收方: {transactions[1].get('to', 'unknown')} | 
         金额: {transactions[1].get('amount', 0)} | 
         节点: {transactions[1].get('node', 'unknown')}
"""
            
            elif pattern.get('type') == 'FORK_DOUBLE_SPENDING':
                fork_info = pattern.get('fork_info', {})
                alert_msg += f"""
分叉信息:
  区块高度: {fork_info.get('height', 'unknown')}
  区块1: {fork_info.get('block1_hash', 'unknown')} (节点: {fork_info.get('block1_node', 'unknown')})
  区块2: {fork_info.get('block2_hash', 'unknown')} (节点: {fork_info.get('block2_node', 'unknown')})
  冲突交易数: {fork_info.get('conflicts', 0)}
"""
                conflicts = pattern.get('conflicts_detail', [])
                if conflicts:
                    alert_msg += "\n冲突详情:\n"
                    for i, conflict in enumerate(conflicts[:3], 1):  # 最多显示3个冲突
                        alert_msg += f"  冲突{i}: {conflict.get('from_address', 'unknown')} -> "
                        alert_msg += f"{conflict.get('to1', 'unknown')}({conflict.get('amount1', 0)}) vs "
                        alert_msg += f"{conflict.get('to2', 'unknown')}({conflict.get('amount2', 0)})\n"
            
            alert_msg += f"{'='*60}\n"
            
            # 输出到控制台
            print(alert_msg)
            
            # 记录到日志
            self.logger.warning(f"ATTACK DETECTED: {pattern.get('attack_id', 'unknown')} - {pattern.get('type', 'UNKNOWN')}")
            
            # 调用回调函数
            for callback in self.alert_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(pattern)
                    else:
                        callback(pattern)
                except Exception as e:
                    self.logger.error(f"Error in callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error formatting alert: {e}")


# 测试用例
if __name__ == "__main__":
    import asyncio
    
    async def test_double_spending_detector():
        """测试双花检测器"""
        print("开始测试双花检测器...")
        
        # 创建检测器
        detector = DoubleSpendingDetector(detection_window=60, similarity_threshold=0.5)
        alert_manager = AttackAlertManager()
        
        # 测试质押交易（应该被跳过）
        print("\n1. 测试质押交易（自己向自己转账）...")
        patterns = detector.add_transaction("node1", {
            'from_address': 'node1',
            'to_address': 'node1',  # 自己向自己转账
            'amount': 20.0,
            'transaction_id': 'stake1'
        })
        print(f"检测结果: {len(patterns)} 个可疑模式 (应该是0)")
        
        # 测试正常交易
        print("\n2. 测试正常交易...")
        patterns = detector.add_transaction("node1", {
            'from_address': 'alice',
            'to_address': 'bob',
            'amount': 100.0,
            'transaction_id': 'tx1'
        })
        print(f"检测结果: {len(patterns)} 个可疑模式")
        
        # 测试双花攻击
        print("\n3. 测试双花攻击...")
        patterns = detector.add_transaction("node1", {
            'from_address': 'alice',
            'to_address': 'charlie',  # 不同接收者
            'amount': 100.0,  # 相同金额
            'transaction_id': 'tx2'
        })
        print(f"检测结果: {len(patterns)} 个可疑模式")
        
        if patterns:
            await alert_manager.send_alert(patterns)
        
        # 显示检测状态
        print("\n4. 检测器状态:")
        status = detector.get_detection_status()
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # 显示攻击历史
        print("\n5. 攻击历史:")
        history = detector.get_attack_history()
        for attack in history:
            print(f"  {attack['attack_id']}: {attack['type']} (置信度: {attack['confidence']:.2f})")
    
    # 运行测试
    asyncio.run(test_double_spending_detector())