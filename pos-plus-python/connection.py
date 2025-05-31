import json
import time
import socket
import logging
import threading
import os
from blockchain import validators, mutex, Blockchain, candidate_blocks, Block
from utilities import calculate_hash, generate_block, is_block_valid
from collections import deque
from dotenv import load_dotenv

# 不在模块级别加载环境变量，改为在需要时加载
# load_dotenv()

# 延迟获取环境变量，确保在main.py中正确加载配置后再获取
def get_server_config():
    """获取服务器配置，确保环境变量已正确加载"""
    return {
        'host': os.getenv("SERVER_HOST", "localhost"),
        'port': int(os.getenv("SERVER_PORT", 9000))
    }

SERVER_HOST = None  # 将在初始化时设置
SERVER_PORT = None  # 将在初始化时设置

# 全局公告队列
announcements = deque()

# 已知交易ID集合，用于双花检测
known_transaction_ids = set()

# 已知节点列表，用于节点间通信
known_nodes = []

def handle_conn(conn, addr):
    try:
        logging.debug(f"开始处理来自 {addr} 的连接")
        # 公告广播线程
        def send_announcements():
            while True:
                if len(announcements) > 0:
                    msg = announcements.pop()
                    try:
                        conn.sendall(msg.encode())
                        logging.debug(f"已发送公告: {msg}")
                    except:
                        pass
                time.sleep(1)  # 避免CPU占用过高
        
        # 启动公告线程
        announcement_thread = threading.Thread(target=send_announcements)
        announcement_thread.daemon = True
        announcement_thread.start()
        
        # 验证者地址
        address = ""
        
        # 请求用户输入代币余额
        conn.sendall(b"Enter token balance:")
        balance_data = conn.recv(1024).strip()
        logging.debug(f"收到代币余额数据: {balance_data}")
        
        try:
            # 尝试解析为JSON格式
            try:
                message = json.loads(balance_data)
                logging.debug(f"成功解析JSON: {message}")
                # 检查是否为注册消息
                if isinstance(message, dict) and message.get("type") == "REGISTER":
                    balance = int(message.get("stake", 0))
                    addr_string = message.get("address", "")
                    if addr_string:
                        address = addr_string
                    else:
                        t = time.time()
                        address = calculate_hash(str(t))
                        
                    # 如果是注册消息，可能包含节点的通信地址和端口
                    node_addr = message.get("node_addr", "")
                    node_port = message.get("node_port", "")
                    
                    if node_addr and node_port:
                        # 添加到已知节点列表
                        node_port = int(node_port)
                        if (node_addr, node_port) not in known_nodes:
                            known_nodes.append((node_addr, node_port))
                            logging.info(f"添加新节点到已知列表: {node_addr}:{node_port}")
                else:
                    # 如果不是注册消息，尝试作为整数处理
                    balance = int(balance_data)
                    t = time.time()
                    address = calculate_hash(str(t))
            except json.JSONDecodeError:
                # 如果不是JSON格式，则尝试作为整数处理
                balance = int(balance_data)
                t = time.time()
                address = calculate_hash(str(t))
            
            with mutex:
                validators[address] = balance
            
            print(validators)
        except ValueError as e:
            logging.error(f"{balance_data} not a number: {e}")
            return
        
        conn.sendall(b"\nEnter current mileage:")
        
        def process_mileage():
            while True:
                mileage_data = conn.recv(1024).strip()
                if not mileage_data:
                    break
                
                logging.debug(f"收到里程数据: {mileage_data}")
                    
                try:
                    # 尝试解析为JSON格式
                    try:
                        message = json.loads(mileage_data)
                        
                        # 处理不同类型的消息
                        if isinstance(message, dict):
                            msg_type = message.get("type", "")
                            
                            # 处理心跳消息
                            if msg_type == "HEARTBEAT":
                                from_node = message.get("from", "")
                                logging.info(f"收到来自 {from_node} 的心跳消息")
                                conn.sendall(json.dumps({
                                    "status": "success", 
                                    "message": "心跳消息已接收"
                                }).encode())
                                continue
                            
                            # 处理交易消息
                            if msg_type == "TRANSACTION":
                                mileage = int(message.get("BPM", 30))
                                transaction_address = message.get("address", address)
                                transaction_id = message.get("id", "")
                                recipient = message.get("recipient", "")
                                amount = message.get("amount", 0)
                                
                                logging.info(f"收到交易: BPM={mileage}, 地址={transaction_address}, ID={transaction_id}")                                # 检查是否为双花交易
                                if transaction_id:
                                    logging.info(f"检查交易ID: {transaction_id}")
                                    # 检查全局已知交易ID集合中是否已存在该ID
                                    if transaction_id in known_transaction_ids:
                                        logging.warning(f"检测到双花尝试! ID: {transaction_id}, 地址: {transaction_address}")
                                        # 立即发送错误响应
                                        error_response = json.dumps({
                                            "status": "error", 
                                            "message": "检测到双花交易尝试"
                                        })
                                        conn.sendall(error_response.encode())
                                        
                                        # 创建警报消息
                                        alert_message = json.dumps({
                                            "type": "ALERT", 
                                            "message": "检测到双花攻击",
                                            "address": transaction_address,
                                            "transaction_id": transaction_id
                                        })
                                        
                                        # 发送警报到所有节点
                                        announcements.append(alert_message)
                                        
                                        # 传播警报到其他节点
                                        propagate_to_other_nodes({
                                            "type": "ALERT", 
                                            "message": "检测到双花攻击",
                                            "address": transaction_address,
                                            "transaction_id": transaction_id
                                        })
                                        
                                        continue
                                    
                                    # 将新交易ID添加到全局已知交易ID集合
                                    known_transaction_ids.add(transaction_id)
                                
                                with mutex:
                                    old_last_index = Blockchain[-1]
                                
                                # 创建新区块
                                new_block, err = generate_block(old_last_index, mileage, transaction_address, 
                                                               transaction_id, recipient, amount)
                                if err:
                                    logging.error(err)
                                    conn.sendall(json.dumps({"status": "error", "message": err}).encode())
                                    continue
                                    
                                if is_block_valid(new_block, old_last_index):
                                    candidate_blocks.append(new_block)
                                    conn.sendall(json.dumps({
                                        "status": "success", 
                                        "message": "交易已接收",
                                        "transaction_id": f"tx_{time.time()}"
                                    }).encode())
                                    
                                    # 创建公告消息
                                    announcement_message = json.dumps({
                                        "type": "NEW_TRANSACTION",
                                        "from": transaction_address,
                                        "BPM": mileage,
                                        "timestamp": time.time()
                                    })
                                    
                                    # 添加到公告队列，通知其他节点有新交易
                                    announcements.append(announcement_message)
                                    
                                    # 传播交易到其他节点
                                    propagate_to_other_nodes({
                                        "type": "TRANSACTION",
                                        "BPM": mileage,
                                        "address": transaction_address,
                                        "recipient": recipient,
                                        "amount": amount,
                                        "id": transaction_id or f"propagated_tx_{time.time()}"
                                    })
                                
                            # 处理查询消息
                            elif msg_type == "QUERY":
                                query_type = message.get("query", "")
                                if query_type == "BLOCKCHAIN_STATUS":
                                    with mutex:
                                        output = json.dumps([block.__dict__ for block in Blockchain])
                                    conn.sendall(output.encode())
                                else:
                                    conn.sendall(json.dumps({"status": "error", "message": "未知的查询类型"}).encode())
                            
                            # 处理其他类型的消息
                            else:
                                # 默认作为里程值处理
                                mileage = int(message.get("BPM", 30))
                                
                                with mutex:
                                    old_last_index = Blockchain[-1]
                                
                                new_block, err = generate_block(old_last_index, mileage, address, "", "", 0)
                                if err:
                                    logging.error(err)
                                    continue
                                    
                                if is_block_valid(new_block, old_last_index):
                                    candidate_blocks.append(new_block)
                    
                    except json.JSONDecodeError:
                        # 如果不是JSON格式，则尝试作为整数处理
                        mileage = int(mileage_data)
                        
                        with mutex:
                            old_last_index = Blockchain[-1]
                        
                        new_block, err = generate_block(old_last_index, mileage, address, "", "", 0)
                        if err:
                            logging.error(err)
                            continue
                        
                        if is_block_valid(new_block, old_last_index):
                            candidate_blocks.append(new_block)
                    
                    conn.sendall(b"\nEnter current mileage:")
                    
                except ValueError as e:
                    logging.error(f"{mileage_data} not a number: {e}")
                    # 检查是否为双花交易
                    try:
                        message = json.loads(mileage_data)
                        if isinstance(message, dict) and message.get("id") == "same_id_123":
                            logging.warning(f"检测到可能的双花攻击! 地址: {message.get('address')}")
                            announcements.append(json.dumps({
                                "type": "ALERT", 
                                "message": "检测到双花攻击",
                                "address": message.get('address')
                            }))
                    except:
                        pass
                        
                    with mutex:
                        if address in validators:
                            del validators[address]
                    conn.close()
                    return
                    
        # 启动处理里程数据的线程
        mileage_thread = threading.Thread(target=process_mileage)
        mileage_thread.daemon = True
        mileage_thread.start()
        
        # 定期广播区块链状态
        broadcast_interval = 60  # 60秒广播一次
        last_broadcast = time.time()
        
        while True:
            current_time = time.time()
            # 每分钟广播一次区块链状态
            if current_time - last_broadcast >= broadcast_interval:
                try:
                    with mutex:
                        output = json.dumps([block.__dict__ for block in Blockchain])
                    conn.sendall((output + "\n").encode())
                    last_broadcast = current_time
                except:
                    break
            
            # 休眠一小段时间，避免CPU占用过高
            time.sleep(1)
            
    except Exception as e:
        logging.error(f"Connection error: {e}")
    finally:
        conn.close()

def initialize_known_nodes():
    """初始化已知节点列表"""
    global known_nodes, SERVER_HOST, SERVER_PORT
    
    # 初始化服务器配置
    config = get_server_config()
    SERVER_HOST = config['host']
    SERVER_PORT = config['port']
    
    # 从环境变量读取已知节点
    known_nodes_str = os.getenv("KNOWN_NODES", "")
    if known_nodes_str:
        try:
            for node_str in known_nodes_str.split(","):
                if ":" in node_str:
                    host, port = node_str.strip().split(":")
                    if (host, int(port)) not in known_nodes:
                        known_nodes.append((host, int(port)))
            
            logging.info(f"从环境变量加载了 {len(known_nodes)} 个已知节点")
        except Exception as e:
            logging.error(f"解析已知节点列表时出错: {e}")
    
    # 确保当前节点不在已知节点列表中
    current_node = (SERVER_HOST, SERVER_PORT)
    if current_node in known_nodes:
        known_nodes.remove(current_node)
        logging.info(f"从已知节点列表中移除了当前节点: {current_node}")

def connect_to_known_nodes():
    """连接到所有已知节点"""
    if not known_nodes:
        logging.warning("没有已知节点可以连接")
        return
    
    logging.info(f"尝试连接到 {len(known_nodes)} 个已知节点")
    for host, port in known_nodes:
        try:
            logging.info(f"尝试连接到节点 {host}:{port}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, int(port)))
            
            # 跳过初始提示
            sock.recv(1024)
            sock.sendall(b"0")
            sock.recv(1024)
            
            # 发送心跳消息
            heartbeat = {
                "type": "HEARTBEAT",
                "from": f"{SERVER_HOST}:{SERVER_PORT}"
            }
            
            sock.sendall(json.dumps(heartbeat).encode())
            
            try:
                response = sock.recv(1024).decode()
                logging.info(f"心跳响应: {response}")
            except:
                logging.warning(f"未收到来自节点 {host}:{port} 的心跳响应")
            
            sock.close()
            logging.info(f"成功连接到节点 {host}:{port}")
        except Exception as e:
            logging.error(f"连接到节点 {host}:{port} 时出错: {e}")

def propagate_to_other_nodes(message):
    """将消息传播到所有已知节点"""
    if not known_nodes:
        logging.warning("没有已知节点可以传播消息")
        return
    
    logging.info(f"正在将消息传播到 {len(known_nodes)} 个已知节点")
    for host, port in known_nodes:
        try:
            logging.info(f"尝试将消息传播到节点 {host}:{port}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, int(port)))
            
            # 跳过初始提示
            sock.recv(1024)
            sock.sendall(b"0")
            sock.recv(1024)
            
            # 发送消息
            sock.sendall(json.dumps(message).encode())
            
            try:
                response = sock.recv(1024).decode()
                logging.info(f"传播响应: {response}")
            except:
                logging.warning(f"未收到来自节点 {host}:{port} 的传播响应")
            
            sock.close()
            logging.info(f"成功将消息传播到节点 {host}:{port}")
        except Exception as e:
            logging.error(f"传播消息到节点 {host}:{port} 时出错: {e}")

# 新增: 实现区块链同步功能
def sync_blockchain_with_peers():
    """从对等节点同步区块链数据"""
    global Blockchain
    
    if not known_nodes:
        logging.warning("没有已知节点可以同步区块链")
        return
    
    longest_chain = None
    max_length = len(Blockchain)
    
    # 遍历所有已知节点
    for host, port in known_nodes:
        if int(port) == SERVER_PORT:
            continue  # 跳过自己
            
        try:
            logging.info(f"尝试从节点 {host}:{port} 同步区块链")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, int(port)))
            
            # 跳过初始提示
            sock.recv(1024)
            sock.sendall(b"0")
            sock.recv(1024)
            
            # 发送区块链状态查询
            sock.sendall(json.dumps({"type": "QUERY", "query": "BLOCKCHAIN_STATUS"}).encode())
            
            response = sock.recv(8192).decode()
            try:
                peer_blockchain = json.loads(response)
                if isinstance(peer_blockchain, list) and len(peer_blockchain) > max_length:
                    # 找到更长的链
                    logging.info(f"发现更长的区块链: 节点={host}:{port}, 长度={len(peer_blockchain)}")
                    longest_chain = peer_blockchain
                    max_length = len(peer_blockchain)
            except json.JSONDecodeError:
                logging.error(f"无法解析来自节点 {host}:{port} 的区块链数据")
            finally:
                sock.close()
        except Exception as e:
            logging.error(f"从节点 {host}:{port} 同步区块链时出错: {e}")
    
    # 如果找到更长的链，替换本地区块链
    if longest_chain and len(longest_chain) > len(Blockchain):
        logging.info(f"使用更长的区块链替换本地链: 旧长度={len(Blockchain)}, 新长度={len(longest_chain)}")
        
        # 转换JSON对象为Block对象
        new_blockchain = []
        for block_data in longest_chain:
            block = Block(
                index=block_data.get("index", 0),
                timestamp=block_data.get("timestamp", ""),
                mileage=block_data.get("mileage", 0),
                hash_value=block_data.get("hash", ""),
                prev_hash=block_data.get("prev_hash", ""),
                validator=block_data.get("validator", ""),
                transaction_id=block_data.get("transaction_id", ""),
                recipient=block_data.get("recipient", ""),
                amount=block_data.get("amount", 0)
            )
            new_blockchain.append(block)
          # 替换区块链
        with mutex:
            Blockchain.clear()
            Blockchain.extend(new_blockchain)

# 新增: 定期同步线程
def periodic_sync():
    """定期与其他节点同步区块链"""
    while True:
        time.sleep(30)  # 每30秒同步一次
        sync_blockchain_with_peers()
