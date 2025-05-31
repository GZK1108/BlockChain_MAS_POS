import os
import logging
import socket
import threading
import time
import json
import sys
import argparse
from dotenv import load_dotenv
from blockchain import Block, Blockchain, temp_blocks, mutex, candidate_blocks
from utilities import calculate_block_hash
from connection import handle_conn, initialize_known_nodes
from consensus import pick_winner

def main():
    # 添加命令行参数支持
    parser = argparse.ArgumentParser(description='POS+ 区块链节点')
    parser.add_argument('--config', type=str, help='配置文件路径', default='.env')
    args = parser.parse_args()
    
    # 加载环境变量，优先使用环境变量指定的配置文件，其次使用命令行参数指定的配置文件
    config_path = os.getenv('DOTENV_PATH', args.config)
    print(f"正在加载配置文件: {config_path}")
    load_dotenv(config_path)
    
    # 检查是否成功加载了ADDR配置
    if not os.getenv("ADDR"):
        print("警告: 未能从配置文件加载ADDR，将使用默认端口9000")
        os.environ["ADDR"] = "9000"
    
    # Set up logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
      # 添加双花检测的调试输出
    from connection import known_transaction_ids, known_nodes
    print("初始化双花检测系统...")
    print(f"已知交易ID: {known_transaction_ids}")
    
    # 初始化已知节点列表
    initialize_known_nodes()
    print(f"已知节点: {known_nodes}")
    
    # Create genesis block
    t = time.time()
    genesis_block = Block()
    genesis_block = Block(0, str(t), 0, calculate_block_hash(genesis_block), "", "", "", "", 0)
    
    print("Genesis Block Created:")
    print(json.dumps(genesis_block.__dict__, indent=2))
    
    Blockchain.append(genesis_block)
    
    # Start TCP server
    server_port = os.getenv("ADDR", "9000")
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('localhost', int(server_port)))
        server.listen(5)
        logging.info(f"Server started on port {server_port}")
    except Exception as e:
        logging.error(f"Error starting server: {e}")
        return
    
    # Start candidate blocks handler
    def handle_candidates():
        while True:
            if candidate_blocks:
                candidate = candidate_blocks.pop(0)
                with mutex:
                    temp_blocks.append(candidate)
    
    candidate_thread = threading.Thread(target=handle_candidates)
    candidate_thread.daemon = True
    candidate_thread.start()
    
    # Start winner selection process
    winner_thread = threading.Thread(target=lambda: [pick_winner() for _ in iter(int, 1)])
    winner_thread.daemon = True
    winner_thread.start()
    
    # Accept connections
    try:
        while True:
            conn, addr = server.accept()
            logging.info(f"New connection from {addr}")
            client_thread = threading.Thread(target=handle_conn, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        logging.info("Server shutting down")
    finally:
        server.close()

if __name__ == "__main__":
    main()
