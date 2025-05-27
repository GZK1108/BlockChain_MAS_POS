import os
import logging
import socket
import threading
import time
import json
from dotenv import load_dotenv
from blockchain import Block, Blockchain, temp_blocks, mutex, candidate_blocks
from utilities import calculate_block_hash
from connection import handle_conn
from consensus import pick_winner

def main():
    # Load environment variables
    load_dotenv()    # Set up logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
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
