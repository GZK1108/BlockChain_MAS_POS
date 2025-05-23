import math

def get_total_attack_probability(node):
    # Define weights for each check
    weights = {
        "majority_block_generation": 0.1,
        "hash_rate_deviation": 0.2,
        "fork_frequency": 0.1,
        "duplicate_txns_unconfirmed": 0.05,
        "double_spending": 0.1,
        "account_balance_discrepancies": 0.1,
        "sudden_network_participant_increase": 0.1,
        "voting_power_manipulation": 0.05,
        "network_spam": 0.05,
        "duplicate_txns_confirmed": 0.05,
        "conflicting_tx_confirmations": 0.05,
        "abrupt_fee_increase": 0.05,
        "large_fund_movements": 0.1,
        "abnormal_smart_contract_activity": 0.1,
        "frequent_network_errors": 0.05,
        "node_resource_overload": 0.1,
    }
    
    # Calculate individual probabilities and aggregate based on weights
    total_probability = 0.0
    
    # Majority Block Generation
    if check_majority_block_generation(node):
        total_probability += weights["majority_block_generation"]
    
    # Hash Rate Deviation
    total_probability += weights["hash_rate_deviation"] * check_hash_rate_deviation(node)
    
    # Fork Frequency
    total_probability += weights["fork_frequency"] * float(check_fork_frequency(node))
    
    # Duplicate Transactions Unconfirmed
    total_probability += weights["duplicate_txns_unconfirmed"] * float(check_duplicate_txns_unconfirmed(node))
    
    # Double Spending
    if check_double_spending(node):
        total_probability += weights["double_spending"]
    
    # Account Balance Discrepancies
    if check_account_balance_discrepancies(node):
        total_probability += weights["account_balance_discrepancies"]
    
    # Sudden Network Participant Increase
    if check_sudden_network_participant_increase(node):
        total_probability += weights["sudden_network_participant_increase"]
    
    # Voting Power Manipulation
    if check_voting_power_manipulation(node):
        total_probability += weights["voting_power_manipulation"]
    
    # Network Spam
    if check_network_spam(node):
        total_probability += weights["network_spam"]
    
    # Duplicate Transactions Confirmed
    total_probability += weights["duplicate_txns_confirmed"] * float(check_duplicate_txns_confirmed(node))
    
    # Conflicting Tx Confirmations
    if check_conflicting_tx_confirmations(node):
        total_probability += weights["conflicting_tx_confirmations"]
    
    # Abrupt Fee Increase
    if check_abrupt_fee_increase(node):
        total_probability += weights["abrupt_fee_increase"]
    
    # Large Fund Movements
    if check_large_fund_movements(node):
        total_probability += weights["large_fund_movements"]
    
    # Abnormal Smart Contract Activity
    if check_abnormal_smart_contract_activity(node):
        total_probability += weights["abnormal_smart_contract_activity"]
    
    # Frequent Network Errors
    if check_frequent_network_errors(node):
        total_probability += weights["frequent_network_errors"]
    
    # Node Resource Overload
    if check_node_resource_overload(node):
        total_probability += weights["node_resource_overload"]
    
    # Normalize the total probability to be between 0 and 1
    total_probability = min(max(total_probability, 0), 1)
    
    return total_probability

# Mock implementation of all check functions
def check_majority_block_generation(node):
    # Access recent blocks and compare count to threshold
    recent_blocks = get_recent_blocks()
    threshold = calculate_threshold()
    return len(recent_blocks) > threshold

def check_hash_rate_deviation(node):
    # Access hash rate history and calculate deviation
    hash_rate_history = get_hash_rate_history()
    current_hash_rate = node.get_current_hash_rate()
    average_hash_rate = calculate_average_hash_rate(hash_rate_history)
    return (current_hash_rate - average_hash_rate) / average_hash_rate

def check_fork_frequency(node):
    # Access recent forks and count involvement
    recent_forks = get_recent_forks()
    return len(recent_forks)

def check_duplicate_txns_unconfirmed(node):
    # Access unconfirmed blocks and count duplicate transactions
    unconfirmed_blocks = get_unconfirmed_blocks()
    return count_duplicate_transactions(unconfirmed_blocks)

def check_double_spending(node):
    # Access transaction history and identify double spending
    transaction_history = get_transaction_history()
    return detect_double_spending(transaction_history)

def check_account_balance_discrepancies(node):
    # Access account balances and check for anomalies
    account_balances = get_account_balances()
    return detect_balance_anomalies(account_balances)

def check_sudden_network_participant_increase(node):
    # Access network participant data and check for sudden increases
    network_participants = get_network_participants()
    return detect_sudden_increase(network_participants)

def check_voting_power_manipulation(node):
    # Access voting data and check for unusual patterns
    voting_data = get_voting_data()
    return detect_manipulation(voting_data)

def check_network_spam(node):
    # Analyze network traffic for spam
    network_traffic = get_network_traffic()
    return analyze_for_spam(network_traffic)

def check_duplicate_txns_confirmed(node):
    # Access confirmed blocks and count duplicate transactions
    confirmed_blocks = get_confirmed_blocks()
    return count_duplicate_transactions(confirmed_blocks)

def check_conflicting_tx_confirmations(node):
    # Access transaction confirmation data and identify conflicts
    confirmation_data = get_confirmation_data()
    return identify_conflicts(confirmation_data)

def check_abrupt_fee_increase(node):
    # Track transaction fees and check for sudden increases
    transaction_fees = get_transaction_fees()
    return detect_sudden_increase(transaction_fees)

def check_large_fund_movements(node):
    # Monitor fund transfers and flag anomalies
    fund_transfers = get_fund_transfers()
    return flag_anomalies(fund_transfers)

def check_abnormal_smart_contract_activity(node):
    # Analyze smart contract interactions and check for unusual patterns
    smart_contract_interactions = get_smart_contract_interactions()
    return analyze_for_anomalies(smart_contract_interactions)

def check_frequent_network_errors(node):
    # Track network errors and check for excessive frequency
    network_errors = get_network_errors()
    return check_excessive_frequency(network_errors)

def check_node_resource_overload(node):
    # Monitor node resource usage and check for overload
    resource_usage = get_node_resource_usage()
    return check_for_overload(resource_usage)

# Mock helper functions (would be implemented in a real system)
def get_recent_blocks():
    return []

def calculate_threshold():
    return 10

def get_hash_rate_history():
    return [1.0, 1.1, 0.9, 1.2]

def calculate_average_hash_rate(history):
    return sum(history) / len(history) if history else 1.0

def get_recent_forks():
    return []

def get_unconfirmed_blocks():
    return []

def count_duplicate_transactions(blocks):
    return 0

def get_transaction_history():
    return []

def detect_double_spending(history):
    return False

def get_account_balances():
    return {}

def detect_balance_anomalies(balances):
    return False

def get_network_participants():
    return []

def detect_sudden_increase(data):
    return False

def get_voting_data():
    return []

def detect_manipulation(data):
    return False

def get_network_traffic():
    return []

def analyze_for_spam(traffic):
    return False

def get_confirmed_blocks():
    return []

def get_confirmation_data():
    return {}

def identify_conflicts(data):
    return False

def get_transaction_fees():
    return []

def get_fund_transfers():
    return []

def flag_anomalies(transfers):
    return False

def get_smart_contract_interactions():
    return []

def analyze_for_anomalies(interactions):
    return False

def get_network_errors():
    return []

def check_excessive_frequency(errors):
    return False

def get_node_resource_usage():
    return {}

def check_for_overload(usage):
    return False
