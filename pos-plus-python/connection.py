import json
import time
import socket
import logging
from blockchain import validators, mutex, Blockchain, candidate_blocks
from utilities import calculate_hash, generate_block, is_block_valid

def handle_conn(conn, addr):
    try:
        # Start a thread for announcements
        def send_announcements():
            while True:
                if len(announcements) > 0:
                    msg = announcements.pop(0)
                    conn.sendall(msg.encode())
        
        # Start the announcement thread
        import threading
        announcement_thread = threading.Thread(target=send_announcements)
        announcement_thread.daemon = True
        announcement_thread.start()
        
        # validator address
        address = ""
        
        # allow user to allocate number of tokens to stake
        conn.sendall(b"Enter token balance:")
        balance_data = conn.recv(1024).strip()
        
        try:
            balance = int(balance_data)
            t = time.time()
            address = calculate_hash(str(t))
            
            with mutex:
                validators[address] = balance
            
            print(validators)
        except ValueError as e:
            logging.error(f"{balance_data} not a number: {e}")
            return
        
        conn.sendall(b"\nEnter current mileage:")
        
        def process_mileage():
            while True:
                mileage_data = conn.recv(1024).strip()
                if not mileage_data:
                    break
                    
                try:
                    mileage = int(mileage_data)
                    
                    with mutex:
                        old_last_index = Blockchain[-1]
                    
                    # create newBlock for consideration to be forged
                    new_block, err = generate_block(old_last_index, mileage, address)
                    if err:
                        logging.error(err)
                        continue
                        
                    if is_block_valid(new_block, old_last_index):
                        candidate_blocks.append(new_block)
                        
                    conn.sendall(b"\nEnter current mileage:")
                    
                except ValueError as e:
                    logging.error(f"{mileage_data} not a number: {e}")
                    with mutex:
                        if address in validators:
                            del validators[address]
                    conn.close()
                    return
        
        # Start mileage processing thread
        mileage_thread = threading.Thread(target=process_mileage)
        mileage_thread.daemon = True
        mileage_thread.start()
        
        # simulate receiving broadcast
        while True:
            time.sleep(60)  # one minute
            with mutex:
                output = json.dumps([block.__dict__ for block in Blockchain])
            conn.sendall((output + "\n").encode())
            
    except Exception as e:
        logging.error(f"Connection error: {e}")
    finally:
        conn.close()
