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
    record = (str(block.index) + block.timestamp + str(block.mileage) + 
              block.prev_hash + block.validator + block.transaction_id + 
              block.recipient + str(block.amount))
    return calculate_hash(record)

# generate_block creates a new block using previous block's hash
def generate_block(old_block, mileage, address, transaction_id="", recipient="", amount=0):
    new_block = Block()
    
    t = time.time()
    
    new_block.index = old_block.index + 1
    new_block.timestamp = str(t)
    new_block.mileage = mileage
    new_block.prev_hash = old_block.hash
    new_block.validator = address
    new_block.transaction_id = transaction_id
    new_block.recipient = recipient
    new_block.amount = amount
    new_block.hash = calculate_block_hash(new_block)
    
    return new_block, None

# is_block_valid makes sure block is valid by checking index
# and comparing the hash of the previous block
# 新增：分叉检测与处理
# 检查新区块是否导致分叉，并记录分叉信息
# 在 is_block_valid 失败时，增加分叉计数

def is_block_valid(new_block, old_block):
    if old_block.index + 1 != new_block.index:
        # 记录分叉
        if hasattr(new_block, 'validator') and new_block.validator in validators:
            node_obj = validators.get(new_block.validator)
            if hasattr(node_obj, 'forks'):
                node_obj.forks += 1
        return False
    if old_block.hash != new_block.prev_hash:
        # 记录分叉
        if hasattr(new_block, 'validator') and new_block.validator in validators:
            node_obj = validators.get(new_block.validator)
            if hasattr(node_obj, 'forks'):
                node_obj.forks += 1
        return False
    if calculate_block_hash(new_block) != new_block.hash:
        return False
    return True
