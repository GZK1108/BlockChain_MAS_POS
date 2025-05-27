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
        
        # 发送两个相互冲突的交易
        for i in range(2):
            transaction = {
                "type": "TRANSACTION",
                "BPM": 30,
                "address": "wallet_address_123",
                "recipient": f"recipient_{i}",
                "amount": 100,
                "id": "same_id_123"  # 使用相同ID尝试双花
            }
            
            sock.send(json.dumps(transaction).encode())
            time.sleep(0.5)
        
        response = sock.recv(1024).decode()
        print(f"Response: {response}")
        return response
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
                print(f"  索引: {block.get('Index', 'N/A')}")
                print(f"  时间戳: {block.get('Timestamp', 'N/A')}")
                print(f"  数据: BPM {block.get('BPM', 'N/A')}")
                print(f"  哈希: {block.get('Hash', 'N/A')[:10]}...")
                print(f"  验证者: {block.get('Validator', 'N/A')}")
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
        
        # 创建注册消息
        registration = {
            "type": "REGISTER",
            "address": address,
            "stake": stake
        }
        
        # 发送注册
        sock.send(json.dumps(registration).encode())
        response = sock.recv(1024).decode()
        print(f"Response: {response}")
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
