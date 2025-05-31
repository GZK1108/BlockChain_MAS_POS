#!/usr/bin/env python
"""
区块链网络状态测试脚本
用于测试多个区块链节点之间的网络连接和同步状态
"""
import socket
import json
import logging
import time
import sys
import concurrent.futures

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def query_node(host, port):
    """查询单个节点的状态"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        logging.info(f"连接到节点 {host}:{port}...")
        sock.connect((host, port))
        
        # 跳过初始提示（代币余额和里程）
        sock.recv(1024)  # 跳过"Enter token balance:"
        sock.sendall(b"0")  # 发送0表示不是验证者
        sock.recv(1024)  # 跳过"Enter current mileage:"
        
        # 查询区块链状态
        query = {
            "type": "QUERY",
            "query": "BLOCKCHAIN_STATUS"
        }
        
        logging.info(f"向节点 {port} 发送区块链状态查询")
        sock.sendall(json.dumps(query).encode())
        
        try:
            response = sock.recv(4096).decode()
            logging.debug(f"来自节点 {port} 的响应: {response[:100]}...")  # 只记录响应的前100个字符
            
            try:
                blockchain_data = json.loads(response)
                if isinstance(blockchain_data, list):
                    return {
                        "port": port,
                        "status": "online",
                        "blockchain_length": len(blockchain_data),
                        "genesis_hash": blockchain_data[0].get("hash") if blockchain_data else None,
                        "latest_block": blockchain_data[-1] if blockchain_data else None
                    }
                else:
                    return {
                        "port": port,
                        "status": "online",
                        "error": f"无法解析区块链数据: {blockchain_data}"
                    }
            except json.JSONDecodeError:
                return {
                    "port": port,
                    "status": "online",
                    "error": "无法解析JSON响应"
                }
        except Exception as e:
            logging.error(f"接收来自节点 {port} 的响应时出错: {e}")
            return {
                "port": port,
                "status": "error",
                "error": str(e)
            }
    except Exception as e:
        logging.error(f"连接到节点 {port} 时出错: {e}")
        return {
            "port": port,
            "status": "offline",
            "error": str(e)
        }
    finally:
        sock.close()

def test_network_synchronization(host='localhost', ports=[9000, 9001, 9002]):
    """测试区块链网络同步状态"""
    print("\n=== 开始区块链网络同步测试 ===")
    print(f"主机: {host}")
    print(f"端口: {ports}")
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(ports)) as executor:
        future_to_port = {executor.submit(query_node, host, port): port for port in ports}
        for future in concurrent.futures.as_completed(future_to_port):
            port = future_to_port[future]
            try:
                data = future.result()
                results.append(data)
            except Exception as exc:
                logging.error(f"处理节点 {port} 时出错: {exc}")
                results.append({
                    "port": port,
                    "status": "error",
                    "error": str(exc)
                })
    
    # 打印结果
    print("\n节点状态:")
    for result in sorted(results, key=lambda x: x["port"]):
        port = result["port"]
        status = result["status"]
        
        if status == "online":
            if "blockchain_length" in result:
                print(f"节点 {port}: 在线, 区块链长度: {result['blockchain_length']}")
                if result.get("latest_block"):
                    latest = result["latest_block"]
                    print(f"  最新区块: #{latest.get('index')}, 验证者: {latest.get('validator')}, BPM: {latest.get('mileage')}")
            else:
                print(f"节点 {port}: 在线, 但无法获取区块链数据: {result.get('error', '未知错误')}")
        else:
            print(f"节点 {port}: {status}, 错误: {result.get('error', '未知错误')}")
    
    # 检查同步状态
    online_nodes = [r for r in results if r["status"] == "online" and "blockchain_length" in r]
    if len(online_nodes) < 2:
        print("\n无法检查同步状态: 在线节点不足")
        return
    
    # 检查创世区块哈希是否一致
    genesis_hashes = set(node.get("genesis_hash") for node in online_nodes if node.get("genesis_hash"))
    if len(genesis_hashes) > 1:
        print("\n同步问题: 节点间创世区块哈希不一致!")
        for i, node in enumerate(online_nodes):
            print(f"节点 {node['port']} 创世区块哈希: {node.get('genesis_hash')}")
    else:
        print("\n创世区块哈希一致: 良好")
    
    # 检查区块链长度
    chain_lengths = [node.get("blockchain_length") for node in online_nodes]
    if len(set(chain_lengths)) > 1:
        print("\n同步问题: 节点间区块链长度不一致!")
        for node in online_nodes:
            print(f"节点 {node['port']} 区块链长度: {node.get('blockchain_length')}")
        
        # 查找最长链
        max_length = max(chain_lengths)
        max_length_nodes = [node for node in online_nodes if node.get("blockchain_length") == max_length]
        print(f"\n最长链在节点: {[node['port'] for node in max_length_nodes]}, 长度: {max_length}")
    else:
        print(f"\n区块链长度一致: {chain_lengths[0]} 个区块")
    
    print("\n=== 区块链网络同步测试完成 ===")

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        host = sys.argv[1]
        ports = [int(p) for p in sys.argv[2:]] if len(sys.argv) > 2 else [9000, 9001, 9002]
        test_network_synchronization(host, ports)
    else:
        print("使用方法: python test_network_sync.py 主机 [端口1 端口2 ...]")
        print("示例: python test_network_sync.py localhost 9000 9001 9002")
        test_network_synchronization()  # 使用默认值
