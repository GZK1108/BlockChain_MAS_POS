#!/usr/bin/env python
"""
交互式发送交易脚本
"""
import socket
import sys
import json
import time
import logging
import uuid

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def send_transaction(host='localhost', port=9000, bpm=30, address="wallet_123", recipient="network", amount=0):
    """发送交易数据到节点"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        logging.info(f"正在连接到 {host}:{port}...")
        sock.connect((host, port))
        
        # 跳过初始提示（代币余额和里程）
        sock.recv(1024)  # 跳过"Enter token balance:"
        sock.sendall(b"0")  # 发送0表示不是验证者
        
        sock.recv(1024)  # 跳过"Enter current mileage:"
        
        # 创建交易消息
        transaction = {
            "type": "TRANSACTION",
            "BPM": bpm,
            "address": address,
            "recipient": recipient,
            "amount": amount,
            "id": f"tx_{uuid.uuid4().hex[:8]}_{time.time()}"
        }
        
        # 发送交易
        logging.info(f"发送交易: {transaction}")
        sock.sendall(json.dumps(transaction).encode())
        
        # 接收响应
        response = sock.recv(1024).decode()
        
        # 尝试解析响应为JSON
        try:
            response_data = json.loads(response)
            logging.info(f"交易响应: {response_data}")
            
            if response_data.get("status") == "success":
                print(f"交易已成功提交!")
                print(f"交易ID: {response_data.get('transaction_id', 'unknown')}")
                
                # 等待确认通知
                print("等待交易确认...")
                
                try:
                    # 监听区块确认
                    timeout = time.time() + 60  # 60秒超时
                    while time.time() < timeout:
                        try:
                            data = sock.recv(4096).decode()
                            if not data:
                                break
                                
                            # 尝试解析JSON数据
                            try:
                                message = json.loads(data)
                                if isinstance(message, dict):
                                    if message.get("type") == "BLOCK_CONFIRMED":
                                        print("\n交易已被确认到区块!")
                                        print(f"区块索引: {message.get('block', {}).get('index')}")
                                        print(f"验证者: {message.get('validator')}")
                                        return True
                            except json.JSONDecodeError:
                                print(f"收到消息: {data}")
                            
                        except socket.timeout:
                            # 超时检查
                            if time.time() >= timeout:
                                print("等待确认超时")
                                break
                            continue
                            
                except KeyboardInterrupt:
                    print("\n停止等待确认")
            else:
                print(f"交易提交失败: {response_data.get('message', '未知错误')}")
                
        except json.JSONDecodeError:
            logging.warning(f"无法解析响应为JSON: {response}")
            print(f"响应: {response}")
        
        return True
    except Exception as e:
        logging.error(f"发送交易时出错: {e}")
        return False
    finally:
        sock.close()

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        host = sys.argv[1]
        port = int(sys.argv[2])
        bpm = int(sys.argv[3])
        address = sys.argv[4] if len(sys.argv) > 4 else "wallet_123"
        recipient = sys.argv[5] if len(sys.argv) > 5 else "network"
        amount = int(sys.argv[6]) if len(sys.argv) > 6 else 0
        send_transaction(host, port, bpm, address, recipient, amount)
    else:
        print("使用方法: python send_transaction.py 主机 端口 BPM [地址] [接收者] [金额]")
        print("示例: python send_transaction.py localhost 9000 30 wallet_123 receiver_456 100")
        send_transaction()  # 使用默认值
