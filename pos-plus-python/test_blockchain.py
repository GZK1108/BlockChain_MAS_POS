#!/usr/bin/env python
"""
区块链功能测试脚本
用于测试区块链系统的基本功能和网络连接状态
"""
import socket
import json
import logging
import time
import sys

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def test_blockchain_functionality(host='localhost', port=9000):
    """测试区块链功能和网络连接状态"""
    print("\n=== 开始区块链功能测试 ===")
    
    # 1. 测试与主节点的连接
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        logging.info(f"连接到主节点 {host}:{port}...")
        sock.connect((host, port))
        
        # 跳过初始提示（代币余额和里程）
        sock.recv(1024)  # 跳过"Enter token balance:"
        sock.sendall(b"0")  # 发送0表示不是验证者
        sock.recv(1024)  # 跳过"Enter current mileage:"
        
        print("与主节点连接成功！")
        
        # 2. 发送心跳消息
        heartbeat = {
            "type": "HEARTBEAT",
            "from": f"test_client_{int(time.time())}"
        }
        
        logging.info(f"发送心跳消息: {heartbeat}")
        sock.sendall(json.dumps(heartbeat).encode())
        
        try:
            response = sock.recv(1024).decode()
            logging.info(f"心跳响应: {response}")
            print(f"心跳测试结果: {response}")
        except Exception as e:
            logging.error(f"接收心跳响应时出错: {e}")
        
        # 3. 查询区块链状态
        query = {
            "type": "QUERY",
            "query": "BLOCKCHAIN_STATUS"
        }
        
        logging.info(f"发送区块链状态查询: {query}")
        sock.sendall(json.dumps(query).encode())
        
        try:
            response = sock.recv(4096).decode()
            logging.debug(f"区块链状态响应: {response}")
            
            try:
                blockchain_data = json.loads(response)
                if isinstance(blockchain_data, list):
                    print(f"\n区块链状态: 包含 {len(blockchain_data)} 个区块")
                    for i, block in enumerate(blockchain_data[:3]):  # 只显示前3个区块
                        print(f"块 #{i}: 验证者={block.get('validator')}, BPM={block.get('mileage')}")
                    if len(blockchain_data) > 3:
                        print(f"... 还有 {len(blockchain_data) - 3} 个区块未显示")
                else:
                    print(f"区块链状态响应: {blockchain_data}")
            except json.JSONDecodeError:
                print(f"无法解析区块链数据: {response}")
        except Exception as e:
            logging.error(f"接收区块链状态响应时出错: {e}")
        
        # 4. 发送测试交易
        test_tx = {
            "type": "TRANSACTION",
            "BPM": 42,
            "address": f"test_address_{int(time.time())}",
            "recipient": "test_recipient",
            "amount": 10,
            "id": f"test_tx_{int(time.time())}"
        }
        
        logging.info(f"发送测试交易: {test_tx}")
        sock.sendall(json.dumps(test_tx).encode())
        
        try:
            response = sock.recv(1024).decode()
            logging.info(f"交易响应: {response}")
            print(f"\n交易测试结果: {response}")
        except Exception as e:
            logging.error(f"接收交易响应时出错: {e}")
        
        # 5. 测试双花检测
        time.sleep(1)  # 等待交易处理
        
        # 使用相同的交易ID但不同的接收者尝试双花
        double_spend_tx = test_tx.copy()
        double_spend_tx["recipient"] = "different_recipient"
        
        logging.info(f"发送双花测试交易: {double_spend_tx}")
        sock.sendall(json.dumps(double_spend_tx).encode())
        
        try:
            response = sock.recv(1024).decode()
            logging.info(f"双花交易响应: {response}")
            print(f"\n双花测试结果: {response}")
            
            # 检查是否检测到双花
            try:
                response_data = json.loads(response)
                if response_data.get("status") == "error" and "双花" in response_data.get("message", ""):
                    print("双花检测成功！系统正确识别了双花尝试")
                else:
                    print("警告: 双花未被检测")
            except:
                print(f"双花测试响应: {response}")
        except Exception as e:
            logging.error(f"接收双花响应时出错: {e}")
        
        # 6. 监听后续消息
        print("\n监听系统消息（10秒）...")
        timeout = time.time() + 10  # 10秒超时
        sock.settimeout(1)  # 设置超时为1秒
        
        while time.time() < timeout:
            try:
                data = sock.recv(1024).decode()
                if not data:
                    continue
                
                try:
                    message = json.loads(data)
                    if isinstance(message, dict):
                        print(f"收到消息: {message}")
                except:
                    print(f"收到原始数据: {data}")
            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"监听消息时出错: {e}")
                break
    
    except Exception as e:
        logging.error(f"测试区块链功能时出错: {e}")
    finally:
        sock.close()
        print("\n=== 区块链功能测试完成 ===")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
        test_blockchain_functionality(host, port)
    else:
        print("使用方法: python test_blockchain.py 主机 端口")
        print("示例: python test_blockchain.py localhost 9000")
        test_blockchain_functionality()  # 使用默认值
