"""
POS+ 区块链客户端
提供与区块链节点交互的功能
"""
import socket
import json
import time
import argparse


def send_transaction(host='localhost', port=9000, bpm=30, address="wallet_address_123"):
    """发送交易数据到节点"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        # 接收并回应初始提示
        prompt = sock.recv(1024).decode()  # 接收"Enter token balance:"
        print(f"Server prompt: {prompt}")
        sock.sendall(b"0")  # 发送0表示不是验证者
        
        prompt = sock.recv(1024).decode()  # 接收"Enter current mileage:"
        print(f"Server prompt: {prompt}")
        
        # 创建交易消息
        transaction = {
            "type": "TRANSACTION",
            "BPM": bpm,
            "address": address  # 钱包地址
        }
        
        # 发送交易
        sock.send(json.dumps(transaction).encode())
        response = sock.recv(1024).decode()
        print(f"Response: {response}")
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        sock.close()


def simulate_double_spending(host='localhost', port=9000):
    """模拟双花攻击行为"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        # 接收并回应初始提示
        prompt = sock.recv(1024).decode()  # 接收"Enter token balance:"
        print(f"Server prompt: {prompt}")
        sock.sendall(b"0")  # 发送0表示不是验证者
        
        prompt = sock.recv(1024).decode()  # 接收"Enter current mileage:"
        print(f"Server prompt: {prompt}")
        
        # 创建一个唯一的交易ID用于双花尝试
        # 生成两个不同的 txid，但第二个和第一个完全相同，实现双花
        tx_id = f"double_spend_{time.time()}"
        sender_address = f"wallet_{time.time()}"
        
        print("\n=== 开始双花攻击模拟 ===")
        print(f"发送者地址: {sender_address}")
        print(f"交易ID: {tx_id}")
        print("========================\n")
        
        # 发送两个相互冲突的交易
        for i in range(2):
            recipient = f"recipient_{i}"
            
            transaction = {
                "type": "TRANSACTION",
                "BPM": 30,
                "address": sender_address,
                "recipient": recipient,
                "amount": 100,                "id": tx_id  # 使用相同ID尝试双花
            }
            
            print(f"发送交易 {i+1} 到接收者 {recipient}")
            print(f"发送数据: {json.dumps(transaction)}")
            sock.send(json.dumps(transaction).encode())
            
            # 等待短暂时间，确保第一个交易被处理
            time.sleep(1)
            
            # 接收响应
            try:
                response = sock.recv(1024).decode()
                print(f"交易 {i+1} 响应: {response}")
                
                try:
                    response_data = json.loads(response)
                    if response_data.get('status') == 'error' and '双花' in response_data.get('message', ''):
                        print(f"\n双花检测成功! 交易 {i+1} 被拒绝")
                        return True
                except:
                    pass
            except:
                print(f"交易 {i+1} 未收到响应")
        
        # 继续监听，看是否有双花警报
        print("\n监听双花警报...")
        timeout = time.time() + 10  # 10秒超时
        
        sock.settimeout(1)  # 设置超时为1秒
        
        while time.time() < timeout:
            try:
                alert_data = sock.recv(1024).decode()
                
                if not alert_data:
                    continue
                    
                print(f"收到消息: {alert_data}")
                
                try:
                    alert = json.loads(alert_data)
                    if isinstance(alert, dict) and alert.get('type') == 'ALERT':
                        print(f"\n收到警报: {alert.get('message')}")
                        print(f"涉及地址: {alert.get('address')}")
                        return True
                except:
                    pass
            except socket.timeout:
                continue
        
        print("\n未收到双花警报")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        sock.close()


def query_blockchain(host='localhost', port=9000):
    """查询区块链当前状态"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        # 接收并回应初始提示
        prompt = sock.recv(1024).decode()  # 接收"Enter token balance:"
        print(f"Server prompt: {prompt}")
        sock.sendall(b"0")  # 发送0表示不是验证者
        
        prompt = sock.recv(1024).decode()  # 接收"Enter current mileage:"
        print(f"Server prompt: {prompt}")
        
        # 创建查询消息
        query = {
            "type": "QUERY",
            "query": "BLOCKCHAIN_STATUS"
        }
        
        # 发送查询
        sock.send(json.dumps(query).encode())
        response = sock.recv(4096).decode()  # 增大接收缓冲区以接收完整区块链
          # 解析并打印区块链
        try:
            blockchain_data = json.loads(response)
            print("\n=== 当前区块链状态 ===")
            for i, block in enumerate(blockchain_data):
                print(f"块 #{i}")
                print(f"  索引: {block.get('index', 'N/A')}")
                print(f"  时间戳: {block.get('timestamp', 'N/A')}")
                print(f"  数据: BPM {block.get('mileage', 'N/A')}")
                print(f"  哈希: {block.get('hash', 'N/A')[:10] if block.get('hash') else 'N/A'}...")
                print(f"  验证者: {block.get('validator', 'N/A')}")
                if block.get('transaction_id'):
                    print(f"  交易ID: {block.get('transaction_id', 'N/A')}")
                if block.get('recipient'):
                    print(f"  接收者: {block.get('recipient', 'N/A')}")
                if block.get('amount'):
                    print(f"  金额: {block.get('amount', 'N/A')}")
            print("=====================\n")
        except:
            print(f"Response: {response}")
        
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        sock.close()


def register_node(host='localhost', port=9000, stake=100, address="new_node_address"):
    """注册新节点到网络"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        # 接收"Enter token balance:"提示
        prompt = sock.recv(1024).decode()
        print(f"Server prompt: {prompt}")
        
        # 创建注册消息
        registration = {
            "type": "REGISTER",
            "address": address,
            "stake": stake
        }
        
        # 发送注册
        sock.send(json.dumps(registration).encode())
        
        # 接收注册响应
        try:
            response = sock.recv(1024).decode()
            print(f"Registration response: {response}")
            
            # 处理第二个提示 - "Enter current mileage:"
            if "Enter current mileage:" in response:
                # 发送一个简单的交易，完成注册过程
                transaction = {
                    "type": "TRANSACTION",
                    "BPM": 30,
                    "address": address
                }
                sock.send(json.dumps(transaction).encode())
                final_response = sock.recv(1024).decode()
                print(f"Final response: {final_response}")
        except Exception as e:
            print(f"Error receiving response: {e}")
        
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        sock.close()


def main():
    """客户端主函数"""
    parser = argparse.ArgumentParser(description="POS+ 区块链客户端")
    parser.add_argument("--host", default="localhost", help="节点主机地址")
    parser.add_argument("--port", type=int, default=9000, help="节点端口")
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 交易命令
    transaction_parser = subparsers.add_parser("transaction", help="发送交易")
    transaction_parser.add_argument("--bpm", type=int, default=30, help="每分钟心跳数")
    transaction_parser.add_argument("--address", default="wallet_address_123", help="钱包地址")
    
    # 模拟双花攻击命令
    subparsers.add_parser("double-spend", help="模拟双花攻击")
    
    # 查询区块链命令
    subparsers.add_parser("query", help="查询区块链状态")
    
    # 注册节点命令
    register_parser = subparsers.add_parser("register", help="注册新节点")
    register_parser.add_argument("--stake", type=int, default=100, help="质押金额")
    register_parser.add_argument("--address", default="new_node_address", help="节点地址")
    
    args = parser.parse_args()
    
    if args.command == "transaction":
        send_transaction(args.host, args.port, args.bpm, args.address)
    elif args.command == "double-spend":
        simulate_double_spending(args.host, args.port)
    elif args.command == "query":
        query_blockchain(args.host, args.port)
    elif args.command == "register":
        register_node(args.host, args.port, args.stake, args.address)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
