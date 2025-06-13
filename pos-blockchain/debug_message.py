import message_pb2

# 创建调试脚本来检查消息结构
def debug_message_structure():
    print("=== 检查protobuf消息结构 ===")
    
    # 创建一个测试消息
    msg = message_pb2.Message()
    msg.type = message_pb2.Message.TRANSACTION
    msg.sender_id = "test_node"
    
    # 检查transaction字段
    print(f"Message type: {type(msg)}")
    print(f"Message dir: {[attr for attr in dir(msg) if not attr.startswith('_')]}")
    
    # 尝试访问transaction字段
    if hasattr(msg, 'transaction'):
        print(f"Has transaction field: True")
        print(f"Transaction type: {type(msg.transaction)}")
        print(f"Transaction dir: {[attr for attr in dir(msg.transaction) if not attr.startswith('_')]}")
        
        # 尝试设置transaction字段
        try:
            msg.transaction.from_address = "test_from"
            msg.transaction.to_address = "test_to"
            msg.transaction.amount = 100.0
            print("Successfully set transaction fields")
        except Exception as e:
            print(f"Error setting transaction fields: {e}")
    else:
        print("No transaction field found")
    
    # 检查所有可能的字段
    print("\n=== 所有字段 ===")
    for field in msg.DESCRIPTOR.fields:
        print(f"Field: {field.name} (type: {field.type})")

if __name__ == "__main__":
    debug_message_structure()