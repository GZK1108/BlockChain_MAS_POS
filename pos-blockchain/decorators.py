# Copyright (c) 2025 An Hongxu
# Peking University - School of Software and Microelectronics
# Email: anhongxu@stu.pku.edu.cn
#
# For academic use only. Commercial usage is prohibited without authorization.

def command(name, help_text=""):
    """Decorator to mark a function as a command."""
    def decorator(func):
        func._is_command = True
        func._command_name = name
        func._help_text = help_text
        return func
    return decorator

def message_handler(msg_type):
    """Decorator to mark a function as a message handler for a specific message type."""
    def decorator(func):
        func._is_message_handler = True
        func._msg_type = msg_type
        return func
    return decorator
