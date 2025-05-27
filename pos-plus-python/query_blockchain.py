#!/usr/bin/env python
"""
查询区块链状态脚本
"""
import socket
import sys
import json
import logging
import time

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def query_blockchain(host='localhost', port=9000, query_type="BLOCKCHAIN_STATUS", params=None):
    """查询区块链当前状态"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        logging.info(f"正在连接到 {host}:{port}...")
        sock.connect((host, port))
        
        # 跳过初始提示（代币余额和里程）
        sock.recv(1024)  # 跳过"Enter token balance:"
        sock.sendall(b"0")  # 发送0表示不是验证者
        
        sock.recv(1024)  # 跳过"Enter current mileage:"
        
        # 创建查询消息
        query = {
            "type": "QUERY",
            "query": query_type
        }
        
        # 添加额外参数
        if params:
            query.update(params)
        
        # 发送查询
        logging.info(f"发送查询: {query}")
        sock.sendall(json.dumps(query).encode())
        
        # 接收响应
        try:
            response = sock.recv(4096).decode()
            logging.debug(f"接收到原始响应: {response}")
            
            # 尝试解析区块链数据
            try:
                blockchain_data = json.loads(response)
                
                if isinstance(blockchain_data, list):
                    # 解析为区块链数据
                    print("\n=== 当前区块链状态 ===")
                    print(f"区块数量: {len(blockchain_data)}")
                    
                    for i, block in enumerate(blockchain_data):
                        print(f"\n块 #{i}")
                        print(f"  索引: {block.get('index')}")
                        print(f"  时间戳: {block.get('timestamp')}")
                        print(f"  数据: BPM {block.get('mileage')}")
                        print(f"  哈希: {block.get('hash')}")
                        print(f"  上一个哈希: {block.get('prev_hash')}")
                        print(f"  验证者: {block.get('validator')}")
                elif isinstance(blockchain_data, dict):
                    # 解析为单个响应
                    if "status" in blockchain_data:
                        print(f"\n查询响应: {blockchain_data.get('status')}")
                        print(f"消息: {blockchain_data.get('message')}")
                    else:
                        print("\n查询结果:")
                        for key, value in blockchain_data.items():
                            print(f"  {key}: {value}")
                
                print("=====================\n")
                return blockchain_data
            except json.JSONDecodeError:
                print(f"无法解析区块链数据: {response}")
                return response
        except Exception as e:
            logging.error(f"接收响应时出错: {e}")
            return None
            
    except Exception as e:
        logging.error(f"查询区块链时出错: {e}")
        return None
    finally:
        sock.close()

def query_validators(host='localhost', port=9000):
    """查询当前验证者信息"""
    return query_blockchain(host, port, "VALIDATORS")

def query_transactions(host='localhost', port=9000):
    """查询待处理交易"""
    return query_blockchain(host, port, "PENDING_TRANSACTIONS")

def query_block(host='localhost', port=9000, block_index=None, block_hash=None):
    """查询特定区块"""
    params = {}
    if block_index is not None:
        params["block_index"] = block_index
    elif block_hash is not None:
        params["block_hash"] = block_hash
    
    return query_blockchain(host, port, "BLOCK", params)

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
        query_type = sys.argv[3] if len(sys.argv) > 3 else "BLOCKCHAIN_STATUS"
        
        if query_type == "BLOCKCHAIN_STATUS":
            query_blockchain(host, port)
        elif query_type == "VALIDATORS":
            query_validators(host, port)
        elif query_type == "PENDING_TRANSACTIONS":
            query_transactions(host, port)
        elif query_type == "BLOCK" and len(sys.argv) > 4:
            block_id = sys.argv[4]
            try:
                # 尝试作为索引解析
                block_index = int(block_id)
                query_block(host, port, block_index=block_index)
            except ValueError:
                # 作为哈希解析
                query_block(host, port, block_hash=block_id)
        else:
            print(f"未知的查询类型: {query_type}")
    else:
        print("使用方法: python query_blockchain.py 主机 端口 [查询类型] [区块ID]")
        print("查询类型:")
        print("  BLOCKCHAIN_STATUS - 获取整个区块链状态")
        print("  VALIDATORS - 获取当前验证者列表")
        print("  PENDING_TRANSACTIONS - 获取待处理交易")
        print("  BLOCK - 获取特定区块 (需要指定区块索引或哈希)")
        print("\n示例:")
        print("  python query_blockchain.py localhost 9000")
        print("  python query_blockchain.py localhost 9000 VALIDATORS")
        print("  python query_blockchain.py localhost 9000 BLOCK 3")
        query_blockchain()  # 使用默认值
