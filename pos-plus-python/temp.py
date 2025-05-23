from malicious_detection import get_network_errors, check_excessive_frequency, get_node_resource_usage, check_for_overload

def check_ddos_attack(node):
    network_errors = get_network_errors()
    is_using_excess = check_excessive_frequency(network_errors)
    
    resource_usage = get_node_resource_usage()
    is_overloading = check_for_overload(resource_usage)
    
    return [is_using_excess, is_overloading]
