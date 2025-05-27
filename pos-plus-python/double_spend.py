#!/usr/bin/env python
"""
模拟双花攻击脚本
这个脚本尝试向区块链网络发送两个具有相同ID但不同接收者的交易，
模拟双花攻击行为。这对于测试系统的安全机制非常重要。
"""
import socket
import sys
import json
import time
import logging
import uuid

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def simulate_double_spending(host='localhost', port=9000, amount=100):
    """模拟双花攻击行为"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        logging.info(f"正在连接到 {host}:{port}...")
        sock.connect((host, port))
        
        # 跳过初始提示（代币余额和里程）
        sock.recv(1024)  # 跳过"Enter token balance:"
        sock.sendall(b"0")  # 发送0表示不是验证者
        
        sock.recv(1024)  # 跳过"Enter current mileage:"
        
        # 创建一个唯一的交易ID用于双花尝试
        tx_id = f"double_spend_{uuid.uuid4().hex[:6]}"
        sender_address = "malicious_wallet_" + uuid.uuid4().hex[:8]
        
        print(f"\n=== 开始双花攻击模拟 ===")
        print(f"发送者地址: {sender_address}")
        print(f"交易ID: {tx_id}")
        print(f"金额: {amount}")
        print("========================\n")
        
        # 发送两个相互冲突的交易
        for i in range(2):
            recipient = f"recipient_{i}_{uuid.uuid4().hex[:4]}"
            
            transaction = {
                "type": "TRANSACTION",
                "BPM": 30,
                "address": sender_address,
                "recipient": recipient,
                "amount": amount,
                "id": tx_id  # 使用相同ID尝试双花
            }
            
            print(f"发送交易 {i+1} 到接收者 {recipient}")
            logging.info(f"发送交易: {transaction}")
            sock.sendall(json.dumps(transaction).encode())
            
            # 等待短暂时间，确保第一个交易被处理
            time.sleep(0.5)
            
            # 接收第一个交易的响应
            try:
                response = sock.recv(1024).decode()
                logging.info(f"收到响应: {response}")
                
                try:
                    response_data = json.loads(response)
                    if i == 0:
                        print(f"第一笔交易响应: {response_data.get('status')} - {response_data.get('message')}")
                    else:
                        print(f"第二笔交易响应: {response_data.get('status')} - {response_data.get('message')}")
                        
                        # 检查是否检测到双花
                        if response_data.get('status') == 'error' and '双花' in response_data.get('message', ''):
                            print("\n双花尝试被成功检测!")
                        else:
                            print("\n警告: 双花尝试未被检测，系统可能存在漏洞!")
                except:
                    print(f"响应: {response}")
            except:
                print("未收到响应")
        
        # 继续监听，看是否有双花警报
        print("\n监听双花警报...")
        timeout = time.time() + 10  # 10秒超时
        
        sock.settimeout(1)  # 设置超时为1秒
        
        while time.time() < timeout:
            try:
                alert_data = sock.recv(1024).decode()
                
                if not alert_data:
                    continue
                    
                try:
                    alert = json.loads(alert_data)
                    if isinstance(alert, dict) and alert.get('type') == 'ALERT':
                        print(f"\n收到警报: {alert.get('message')}")
                        print(f"涉及地址: {alert.get('address')}")
                        return True
                except:
                    print(f"收到消息: {alert_data}")
            except socket.timeout:
                continue
        
        print("\n未收到双花警报")
        return False
        
    except Exception as e:
        logging.error(f"模拟双花攻击时出错: {e}")
        return False
    finally:
        sock.close()

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
        amount = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        simulate_double_spending(host, port, amount)
    else:
        print("使用方法: python double_spend.py 主机 端口 [金额]")
        print("示例: python double_spend.py localhost 9000 100")
        simulate_double_spending()  # 使用默认值
