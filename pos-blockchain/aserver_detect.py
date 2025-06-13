# aserver1.py - 带双花攻击检测的区块链服务器
# Copyright (c) 2025 GZK
# Peking University - School of Software and Microelectronics
#
# For academic use only. Commercial usage is prohibited without authorization.

import asyncio
import sys
import struct
import message_pb2
import contextlib

from utils import load_config
from logger import setup_logger
from decorators import message_handler, command
from aserver import BlockchainServerAsync

# 安全导入攻击检测模块
try:
    from attack_detect import DoubleSpendingDetector, AttackAlertManager
    ATTACK_DETECTION_AVAILABLE = True
    print("✓ Attack detection module loaded successfully")
except ImportError as e:
    print(f"Warning: Attack detection not available: {e}")
    ATTACK_DETECTION_AVAILABLE = False
    
    # 更安全的占位符类
    class DoubleSpendingDetector:
        def __init__(self, *args, **kwargs): 
            self.similarity_threshold = 0.8
            self.detection_window = 60
            
        def add_transaction(self, node_id, transaction_data): 
            return []
            
        def add_block(self, node_id, block_data): 
            return []
            
        def get_detection_status(self): 
            return {
                'detection_window': self.detection_window,
                'similarity_threshold': self.similarity_threshold,
                'monitored_nodes': 0,
                'total_attacks_detected': 0,
                'recent_transactions': {},
                'transactions_by_sender': {},
                'recent_blocks': {}
            }
            
        def get_attack_history(self): 
            return []
            
        def set_threshold(self, threshold): 
            try:
                self.similarity_threshold = float(threshold)
                return True
            except:
                return False
    
    class AttackAlertManager:
        def __init__(self): pass
        def add_alert_callback(self, callback): pass
        async def send_alert(self, patterns): pass

logger = setup_logger("server")

class AttackDetectionServer(BlockchainServerAsync):
    """继承基础服务器并添加双花检测功能"""
    
    def __init__(self, host, port, debug_mode=False):
        super().__init__(host, port, debug_mode)
        
        # 初始化攻击检测系统
        self._init_attack_detection()

    def _init_attack_detection(self):
        """初始化攻击检测系统"""
        try:
            # 创建检测器，使用较低的阈值以便更容易检测到双花
            self.attack_detector = DoubleSpendingDetector(
                detection_window=60,  # 60秒检测窗口
                similarity_threshold=0.8  # 较低的阈值，更敏感
            )
            
            # 创建警报管理器
            self.alert_manager = AttackAlertManager()
            
            # 添加攻击检测回调（如果模块可用）
            if ATTACK_DETECTION_AVAILABLE:
                self.alert_manager.add_alert_callback(self._on_attack_detected)
                logger.info("✓ Attack detection system initialized successfully")
                logger.info(f"  - Detection window: {self.attack_detector.detection_window}s")
                logger.info(f"  - Similarity threshold: {self.attack_detector.similarity_threshold}")
            else:
                logger.warning("⚠ Attack detection using fallback implementation")
                
        except Exception as e:
            logger.error(f"Error initializing attack detection: {e}")
            # 使用占位符实现
            self.attack_detector = DoubleSpendingDetector()
            self.alert_manager = AttackAlertManager()

    async def _handle_message(self, writer, message):
        """重写消息处理以添加攻击检测"""
        try:
            # 先进行攻击检测
            await self._detect_and_alert_double_spending(writer, message)
            
            # 然后调用父类的消息处理逻辑
            await super()._handle_message(writer, message)
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            import traceback
            logger.debug(f"Message handling traceback: {traceback.format_exc()}")

    async def _on_attack_detected(self, attack_pattern):
        """攻击检测回调函数"""
        attack_type = attack_pattern.get('type', 'UNKNOWN')
        confidence = attack_pattern.get('confidence', 0)
        attack_id = attack_pattern.get('attack_id', 'unknown')
        
        logger.warning(f"🚨 ATTACK DETECTED: {attack_type} (ID: {attack_id}, Confidence: {confidence:.2%})")
        
        # 可以在这里添加更多的响应逻辑，比如：
        # - 记录到特殊日志文件
        # - 发送邮件通知
        # - 触发其他安全措施等

    def _extract_transaction_from_message(self, msg):
        """从消息中提取交易数据 - 使用正确的字段名 tx"""
        try:
            logger.debug(f"[EXTRACT] Message type: {msg.type}")
            logger.debug(f"[EXTRACT] Message fields: {[f.name for f in msg.DESCRIPTOR.fields]}")
            
            tx_data = None
            
            # 检查正确的交易字段: tx
            if hasattr(msg, 'tx'):
                logger.debug("[EXTRACT] Found tx field")
                tx_data = self._parse_transaction_object(msg.tx)
            else:
                logger.error("[EXTRACT] No tx field found in message")
                logger.debug(f"[EXTRACT] Available fields: {[attr for attr in dir(msg) if not attr.startswith('_')]}")
                return None
            
            return tx_data
            
        except Exception as e:
            logger.error(f"Error extracting transaction from message: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None

    def _parse_transaction_object(self, tx_obj):
        """解析交易对象"""
        try:
            logger.debug(f"[PARSE] Transaction object type: {type(tx_obj)}")
            logger.debug(f"[PARSE] Transaction object fields: {[attr for attr in dir(tx_obj) if not attr.startswith('_')]}")
            
            # 打印交易对象的详细信息
            logger.debug(f"[PARSE] Transaction object: {tx_obj}")
            
            tx_data = {}
            
            # 尝试不同的字段名称组合
            from_fields = ['from_address', 'from_addr', 'sender', 'sender_address', 'from']
            to_fields = ['to_address', 'to_addr', 'receiver', 'recipient', 'recipient_address', 'to']
            amount_fields = ['amount', 'value', 'quantity']
            id_fields = ['transaction_id', 'tx_id', 'id', 'hash']
            
            # 提取from地址
            for field in from_fields:
                if hasattr(tx_obj, field):
                    value = getattr(tx_obj, field)
                    if value:
                        tx_data['from_address'] = str(value)
                        logger.debug(f"[PARSE] Found from_address in field '{field}': {value}")
                        break
            
            # 提取to地址
            for field in to_fields:
                if hasattr(tx_obj, field):
                    value = getattr(tx_obj, field)
                    if value:
                        tx_data['to_address'] = str(value)
                        logger.debug(f"[PARSE] Found to_address in field '{field}': {value}")
                        break
            
            # 提取金额
            for field in amount_fields:
                if hasattr(tx_obj, field):
                    value = getattr(tx_obj, field)
                    if value is not None:
                        tx_data['amount'] = float(value)
                        logger.debug(f"[PARSE] Found amount in field '{field}': {value}")
                        break
            
            # 提取ID
            for field in id_fields:
                if hasattr(tx_obj, field):
                    value = getattr(tx_obj, field)
                    if value:
                        tx_data['transaction_id'] = str(value)
                        logger.debug(f"[PARSE] Found transaction_id in field '{field}': {value}")
                        break
            
            # 检查必需字段
            required_fields = ['from_address', 'to_address', 'amount']
            missing_fields = [field for field in required_fields if field not in tx_data or not tx_data[field]]
            
            if missing_fields:
                logger.warning(f"[PARSE] Missing required fields: {missing_fields}")
                logger.debug(f"[PARSE] Available fields in transaction object:")
                for attr in dir(tx_obj):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(tx_obj, attr)
                            logger.debug(f"  {attr}: {value} (type: {type(value)})")
                        except:
                            logger.debug(f"  {attr}: <error accessing>")
                return None
            
            logger.info(f"[PARSE] Successfully parsed transaction: {tx_data}")
            return tx_data
            
        except Exception as e:
            logger.error(f"Error parsing transaction object: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None

    async def _detect_and_alert_double_spending(self, writer, msg):
        """检测双花攻击并发送警报"""
        if not ATTACK_DETECTION_AVAILABLE:
            logger.debug("[ATTACK_DETECT] Attack detection not available")
            return
            
        try:
            node_id = self.clients.get(writer, "unknown")
            
            if msg.type == message_pb2.Message.TRANSACTION:
                logger.info(f"[ATTACK_DETECT] ===== PROCESSING TRANSACTION from {node_id} =====")
                
                try:
                    # 使用正确的字段名提取交易数据
                    tx_data = self._extract_transaction_from_message(msg)
                    
                    if tx_data is None:
                        logger.error(f"[ATTACK_DETECT] Failed to extract transaction data")
                        return
                    
                    logger.info(f"[ATTACK_DETECT] TX DATA: {tx_data}")
                    
                    # 验证数据完整性
                    if not tx_data.get('from_address') or not tx_data.get('to_address') or tx_data.get('amount', 0) <= 0:
                        logger.warning(f"[ATTACK_DETECT] Incomplete transaction data: {tx_data}")
                        return
                    
                    logger.info(f"[ATTACK_DETECT] Calling detector.add_transaction({node_id}, {tx_data})")
                    
                    # 检测交易级双花
                    patterns = self.attack_detector.add_transaction(node_id, tx_data)
                    
                    logger.info(f"[ATTACK_DETECT] Detector returned {len(patterns)} patterns")
                    
                    if patterns:
                        logger.warning(f"[ATTACK_DETECT] *** SUSPICIOUS PATTERNS FOUND! ***")
                        for i, pattern in enumerate(patterns):
                            logger.warning(f"[ATTACK_DETECT] Pattern {i+1}: {pattern.get('type', 'UNKNOWN')} - confidence: {pattern.get('confidence', 0):.2%}")
                        
                        # 发送双花警报
                        await self.alert_manager.send_alert(patterns)
                    else:
                        logger.info(f"[ATTACK_DETECT] No suspicious patterns detected")
                    
                except Exception as e:
                    logger.error(f"Error processing TRANSACTION message: {e}")
                    import traceback
                    logger.debug(f"Transaction processing traceback: {traceback.format_exc()}")
                    return
                    
            elif msg.type == message_pb2.Message.BLOCK:
                logger.info(f"[ATTACK_DETECT] ===== PROCESSING BLOCK from {node_id} =====")
                
                try:
                    # 检查消息结构
                    if not hasattr(msg, 'block'):
                        logger.error(f"[ATTACK_DETECT] Message has no block field")
                        return
                    
                    # 安全地解析区块数据
                    block_data = self._safe_get_block_data(msg.block)
                    
                    if block_data is None:
                        logger.error(f"[ATTACK_DETECT] Failed to extract block data")
                        return
                    
                    logger.info(f"[ATTACK_DETECT] BLOCK: height={block_data['height']} with {len(block_data['transactions'])} transactions")
                    
                    # 检测分叉级双花
                    patterns = self.attack_detector.add_block(node_id, block_data)
                    
                    if patterns:
                        logger.warning(f"[ATTACK_DETECT] Found {len(patterns)} suspicious block patterns!")
                        await self.alert_manager.send_alert(patterns)
                    
                except Exception as e:
                    logger.error(f"Error processing BLOCK message: {e}")
                    import traceback
                    logger.debug(f"Block processing traceback: {traceback.format_exc()}")
                    return
            else:
                # 其他消息类型不处理
                return
                
        except Exception as e:
            logger.error(f"Error in attack detection: {e}")
            import traceback
            logger.debug(f"Attack detection traceback: {traceback.format_exc()}")

    def _safe_get_block_data(self, block_msg):
        """安全地从protobuf消息中提取区块数据"""
        try:
            logger.debug(f"[EXTRACT] Block message type: {type(block_msg)}")
            logger.debug(f"[EXTRACT] Block message dir: {dir(block_msg)}")
            
            # 检查是否有必要的字段
            if not hasattr(block_msg, 'height'):
                logger.debug(f"[EXTRACT] Block message missing height field")
                return None
                
            block_data = {}
            
            # 安全地获取各个字段
            try:
                block_data['height'] = int(getattr(block_msg, 'height', 0))
            except:
                block_data['height'] = 0
                
            try:
                block_data['parent_hash'] = str(getattr(block_msg, 'parent_hash', ''))
            except:
                block_data['parent_hash'] = ''
                
            try:
                block_data['hash'] = str(getattr(block_msg, 'hash', ''))
            except:
                block_data['hash'] = ''
            
            # 安全地获取交易列表
            transactions = []
            try:
                if hasattr(block_msg, 'transactions'):
                    logger.debug(f"[EXTRACT] Block has {len(block_msg.transactions)} transactions")
                    for i, tx in enumerate(block_msg.transactions):
                        logger.debug(f"[EXTRACT] Processing transaction {i}")
                        tx_data = self._parse_transaction_object(tx)
                        if tx_data:
                            transactions.append(tx_data)
                            logger.debug(f"[EXTRACT] Successfully added transaction {i}: {tx_data}")
                        else:
                            logger.debug(f"[EXTRACT] Failed to parse transaction {i}")
            except Exception as e:
                logger.debug(f"Error processing block transactions: {e}")
                
            block_data['transactions'] = transactions
            
            logger.debug(f"Extracted block data: height={block_data['height']}, transactions={len(transactions)}")
            return block_data
            
        except Exception as e:
            logger.error(f"Error extracting block data: {e}")
            import traceback
            logger.debug(f"Extraction traceback: {traceback.format_exc()}")
            return None

    # ==================== 攻击检测相关命令 ====================

    @command("detect", "显示双花攻击检测状态")
    async def _cmd_detect(self, args):
        """显示双花攻击检测状态"""
        try:
            status = self.attack_detector.get_detection_status()
            
            print(f"\n{'='*50}")
            print(f"双花攻击检测器状态")
            print(f"{'='*50}")
            print(f"检测窗口: {status.get('detection_window', 0)}秒")
            print(f"相似度阈值: {status.get('similarity_threshold', 0)}")
            print(f"监控的节点数: {status.get('monitored_nodes', 0)}")
            print(f"已检测攻击数: {status.get('total_attacks_detected', 0)}")
            
            print(f"\n节点交易统计:")
            tx_stats = status.get('recent_transactions', {})
            if tx_stats:
                for node_id, count in tx_stats.items():
                    print(f"  {node_id}: {count} 个最近交易")
            else:
                print("  暂无监控交易")
            
            print(f"\n发送者交易统计:")
            sender_stats = status.get('transactions_by_sender', {})
            if sender_stats:
                for sender, count in sender_stats.items():
                    print(f"  {sender}: {count} 个交易")
            else:
                print("  暂无发送者交易")
            
            print(f"\n节点区块统计:")
            block_stats = status.get('recent_blocks', {})
            if block_stats:
                for node_id, count in block_stats.items():
                    print(f"  {node_id}: {count} 个最近区块")
            else:
                print("  暂无监控区块")
            
            print(f"{'='*50}")
                
        except Exception as e:
            logger.error(f"Error in detect command: {e}")
            print("检测器状态获取失败")

    @command("attacks", "显示攻击历史")
    async def _cmd_attacks(self, args):
        """显示攻击历史"""
        try:
            attacks = self.attack_detector.get_attack_history()
            
            if not attacks:
                print("\n暂无检测到的攻击")
                return
            
            print(f"\n{'='*60}")
            print(f"检测到的攻击历史 (共 {len(attacks)} 个)")
            print(f"{'='*60}")
            
            for i, attack in enumerate(attacks[-10:], 1):  # 显示最近10个
                print(f"\n{i}. 攻击ID: {attack.get('attack_id', 'unknown')}")
                print(f"   类型: {attack.get('type', 'UNKNOWN')}")
                print(f"   严重程度: {attack.get('severity', 'UNKNOWN')}")
                confidence = attack.get('confidence', 0)
                if isinstance(confidence, (int, float)):
                    print(f"   置信度: {confidence:.2%}")
                else:
                    print(f"   置信度: {confidence}")
                print(f"   时间: {attack.get('detection_time', 'unknown')}")
                print(f"   描述: {attack.get('description', 'No description')}")
                
                # 显示涉及的交易
                if attack.get('type') == 'POTENTIAL_DOUBLE_SPENDING':
                    txs = attack.get('transactions', [])
                    if len(txs) >= 2:
                        print(f"   涉及交易:")
                        print(f"     TX1: {txs[0].get('to', 'unknown')} 金额 {txs[0].get('amount', 0)}")
                        print(f"     TX2: {txs[1].get('to', 'unknown')} 金额 {txs[1].get('amount', 0)}")
                        
            print(f"{'='*60}")
                        
        except Exception as e:
            logger.error(f"Error in attacks command: {e}")
            print("攻击历史获取失败")

    @command("threshold", "设置双花检测阈值")
    async def _cmd_threshold(self, args):
        """设置双花检测阈值"""
        try:
            if not args:
                current = getattr(self.attack_detector, 'similarity_threshold', 0.8)
                print(f"当前阈值: {current}")
                print("用法: threshold <0.0-1.0>")
                print("建议值:")
                print("  0.1-0.3: 非常敏感（可能误报）")
                print("  0.3-0.5: 中等敏感（推荐）")
                print("  0.5-0.8: 保守（较少误报）")
                return
            
            threshold = float(args[0])
            if self.attack_detector.set_threshold(threshold):
                print(f"✓ 双花检测阈值设置为: {threshold}")
                if threshold < 0.3:
                    print("⚠ 警告: 阈值较低，可能产生较多误报")
                elif threshold > 0.7:
                    print("⚠ 警告: 阈值较高，可能漏检一些攻击")
            else:
                print("✗ 阈值必须在 0.0 到 1.0 之间")
        except ValueError:
            print("✗ 请输入有效的数字")
        except Exception as e:
            logger.error(f"Error in threshold command: {e}")
            print("阈值设置失败")

    @command("clear_attacks", "清空攻击历史")
    async def _cmd_clear_attacks(self, args):
        """清空攻击历史"""
        try:
            if hasattr(self.attack_detector, 'detected_attacks'):
                old_count = len(self.attack_detector.detected_attacks)
                self.attack_detector.detected_attacks.clear()
                print(f"✓ 已清空 {old_count} 条攻击记录")
            else:
                print("✗ 无法访问攻击历史")
        except Exception as e:
            logger.error(f"Error clearing attacks: {e}")
            print("清空攻击历史失败")

    @command("help", "Show available server commands")
    async def _cmd_help(self, args):
        print("\n" + "="*60)
        print("Available server commands:")
        print("="*60)
        
        # 分类显示命令
        categories = {
            "攻击检测": ["detect", "attacks", "threshold", "clear_attacks"],
            "服务器控制": ["step", "stop", "continue", "exit"],
            "网络模拟": ["drop", "delay"],
            "帮助": ["help"]
        }
        
        for category, cmd_list in categories.items():
            print(f"\n{category}:")
            for name in cmd_list:
                if name in self.commands:
                    info = self.commands[name]
                    print(f"  {name.ljust(15)} - {info['help']}")
        
        print("="*60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Blockchain Server with Double Spending Detection")
    parser.add_argument("--debug", action="store_true", help="Run server in debug mode (manual STEP)")
    args = parser.parse_args()
    
    # 加载配置
    server_config = load_config(section="server")
    host = server_config.get("host", "localhost")
    port = int(server_config.get("port", 5000))
    
    # 启动服务器
    print(f"Starting Blockchain Server with Attack Detection...")
    print(f"Host: {host}, Port: {port}")
    print(f"Debug mode: {args.debug}")
    
    server = AttackDetectionServer(host=host, port=port, debug_mode=args.debug)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n\nServer interrupted by user. Shutting down...")
    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()