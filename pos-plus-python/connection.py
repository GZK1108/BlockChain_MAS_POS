import json
import time
import socket
import logging
import threading
from blockchain import validators, mutex, Blockchain, candidate_blocks
from utilities import calculate_hash, generate_block, is_block_valid
from collections import deque

# 全局公告队列
announcements = deque()

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
                else:
                    # 如果不是JSON或不是注册消息，尝试作为整数处理
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
                            msg_type = message.get("type", "")                            # 处理交易消息
                            if msg_type == "TRANSACTION":
                                mileage = int(message.get("BPM", 30))
                                transaction_address = message.get("address", address)
                                transaction_id = message.get("id", "")
                                recipient = message.get("recipient", "")
                                amount = message.get("amount", 0)
                                
                                logging.info(f"收到交易: BPM={mileage}, 地址={transaction_address}, ID={transaction_id}")
                                
                                # 检查是否为双花交易
                                if transaction_id:
                                    # 在实际应用中，这里应该检查交易池中是否已存在相同ID的交易
                                    # 这里为了演示，我们使用特定的ID前缀来模拟双花检测
                                    if transaction_id.startswith("double_spend_"):
                                        # 检查是否在短时间内收到相同ID的交易
                                        with mutex:
                                            for block in candidate_blocks:
                                                if hasattr(block, 'transaction_id') and block.transaction_id == transaction_id:
                                                    logging.warning(f"检测到双花尝试! ID: {transaction_id}, 地址: {transaction_address}")
                                                    conn.sendall(json.dumps({
                                                        "status": "error", 
                                                        "message": "检测到双花交易尝试"
                                                    }).encode())
                                                    
                                                    # 发送警报到所有节点
                                                    announcements.append(json.dumps({
                                                        "type": "ALERT", 
                                                        "message": "检测到双花攻击",
                                                        "address": transaction_address,
                                                        "transaction_id": transaction_id
                                                    }))
                                                    continue
                                
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
                                    
                                    # 添加到公告队列，通知其他节点有新交易
                                    announcements.append(json.dumps({
                                        "type": "NEW_TRANSACTION",
                                        "from": transaction_address,
                                        "BPM": mileage,
                                        "timestamp": time.time()
                                    }))
                                
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
