import threading

# Block represents each 'item' in the blockchain
class Block:
    def __init__(self, index=0, timestamp="", mileage=0, hash_value="", prev_hash="", validator="", transaction_id="", recipient="", amount=0):
        self.index = index
        self.timestamp = timestamp
        self.mileage = mileage
        self.hash = hash_value
        self.prev_hash = prev_hash
        self.validator = validator
        self.transaction_id = transaction_id
        self.recipient = recipient
        self.amount = amount

class Node:
    def __init__(self):
        self.blocks_generated = 0
        self.hash_rate = 0.0
        self.average_hash_rate = 0.0
        self.forks = 0
        self.reputation = []
    
    def get_current_hash_rate(self):
        return self.hash_rate

# Blockchain is a series of validated Blocks
Blockchain = []
temp_blocks = []

# candidate_blocks handles incoming blocks for validation
candidate_blocks = []

# announcements broadcasts winning validator to all nodes
announcements = []

mutex = threading.Lock()

# validators keeps track of open validators and balances
validators = {}
