import hashlib
import time
from blockchain import Block

# SHA256 hasing
# calculate_hash is a simple SHA256 hashing function
def calculate_hash(s):
    encoded = s.encode()
    return hashlib.sha256(encoded).hexdigest()

# calculate_block_hash returns the hash of all block information
def calculate_block_hash(block):
    record = str(block.index) + block.timestamp + str(block.mileage) + block.prev_hash
    return calculate_hash(record)

# generate_block creates a new block using previous block's hash
def generate_block(old_block, mileage, address):
    new_block = Block()
    
    t = time.time()
    
    new_block.index = old_block.index + 1
    new_block.timestamp = str(t)
    new_block.mileage = mileage
    new_block.prev_hash = old_block.hash
    new_block.hash = calculate_block_hash(new_block)
    new_block.validator = address
    
    return new_block, None

# is_block_valid makes sure block is valid by checking index
# and comparing the hash of the previous block
def is_block_valid(new_block, old_block):
    if old_block.index + 1 != new_block.index:
        return False
    
    if old_block.hash != new_block.prev_hash:
        return False
    
    if calculate_block_hash(new_block) != new_block.hash:
        return False
    
    return True
