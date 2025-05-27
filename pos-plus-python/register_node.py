#!/usr/bin/env python
"""
交互式节点注册脚本
"""
import socket
import sys
import time
import json
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def register_node(host='localhost', port=9000, stake=100, address=None):
    """交互式注册节点到网络"""
    if address is None:
        # 生成唯一地址（使用时间戳和端口）
        address = f"node_{time.time()}_{port}"
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        logging.info(f"正在连接到 {host}:{port}...")
        sock.connect((host, port))
          # 第一个提示：输入代币余额
        prompt = sock.recv(1024).decode()
        logging.debug(f"接收到: {prompt}")
        
        # 发送JSON格式的注册消息
        register_msg = {
            "type": "REGISTER",
            "address": address,
            "stake": stake
        }
        
        logging.info(f"发送节点注册信息: {register_msg}")
        sock.sendall(json.dumps(register_msg).encode())
          # 第二个提示：输入当前里程
        prompt = sock.recv(1024).decode()
        logging.debug(f"接收到: {prompt}")
        
        # 发送初始区块数据
        initial_block = {
            "type": "INITIAL_BLOCK",
            "BPM": 30
        }
        sock.sendall(json.dumps(initial_block).encode())
        
        # 接收响应
        response = sock.recv(1024).decode()
        logging.info(f"注册响应: {response}")
        
        # 保持连接活跃，监听区块链更新
        print(f"节点 {address} 已成功注册到网络，质押金额: {stake}")
        print("正在监听区块链更新...")
        
        try:
            while True:
                data = sock.recv(4096).decode()
                if not data:
                    break
                    
                # 尝试解析JSON数据
                try:
                    message = json.loads(data)
                    if isinstance(message, dict):
                        if message.get("type") == "BLOCK_CONFIRMED":
                            print("\n新区块已确认!")
                            print(f"验证者: {message.get('validator')}")
                            print(f"区块索引: {message.get('block', {}).get('index')}")
                            print(f"区块哈希: {message.get('block', {}).get('hash')}")
                        elif message.get("type") == "NEW_TRANSACTION":
                            print(f"\n收到新交易: {message}")
                    else:
                        # 处理区块链数据数组
                        print("\n当前区块链状态:")
                        for i, block in enumerate(message):
                            print(f"块 #{i}: 哈希={block.get('hash', '')[:10]}...")
                except json.JSONDecodeError:
                    print(f"收到消息: {data}")
                
        except KeyboardInterrupt:
            print("\n正在断开连接...")
        
        return True    
    except Exception as e:
        logging.error(f"注册节点时出错: {e}")
        return False
    finally:
        sock.close()

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        host = sys.argv[1]
        port = int(sys.argv[2])
        stake = int(sys.argv[3])
        address = sys.argv[4] if len(sys.argv) > 4 else None
        register_node(host, port, stake, address)
    else:
        print("使用方法: python register_node.py 主机 端口 质押金额 [地址]")
        print("示例: python register_node.py localhost 9000 100")
        register_node()  # 使用默认值
