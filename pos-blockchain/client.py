# Copyright (c) 2025 An Hongxu
# Peking University - School of Software and Microelectronics
# Email: anhongxu@stu.pku.edu.cn
#
# For academic use only. Commercial usage is prohibited without authorization.

import socket
import select
import sys
import message_pb2

class Client:
    def __init__(self, client_id, server_host, server_port, logger):
        self.client_id = client_id
        self.logger = logger
        self.handlers = {} # msg_type -> handler 

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((server_host, server_port))
        self.sock.setblocking(False)

        # 发送 hello 消息
        hello_msg = message_pb2.Message()
        hello_msg.type = message_pb2.Message.HELLO
        hello_msg.sender_id = client_id
        self.send(hello_msg)

    def register_handlers(self, obj):
        """从指定对象注册 handler 方法"""
        for attr in dir(obj):
            method = getattr(obj, attr)
            if callable(method) and hasattr(method, "_is_message_handler"):
                msg_type = method._msg_type
                self.handlers[msg_type] = method
                self.logger.debug(f"Registered handler for type {msg_type}: {method.__name__} from {obj.__class__.__name__}")

    def send(self, msg):
        """发送消息到服务器"""
        data = msg.SerializeToString()
        length_prefix = len(data).to_bytes(4, byteorder='big')
        try:
            self.sock.sendall(length_prefix + data)
        except Exception as e:
            self.logger.error(f"Send error: {e}")

    def _recv_full_message(self):
        """接收完整的消息"""
        try:
            header = self.sock.recv(4)
            if len(header) < 4:
                return None
            length = int.from_bytes(header, byteorder='big')
            data = b''
            while len(data) < length:
                packet = self.sock.recv(length - len(data))
                if not packet:
                    break
                data += packet
            return data
        except:
            return None

    def receive_and_dispatch(self):
        """接收消息并分发到对应的 handler"""
        data = self._recv_full_message()
        if not data:
            self.logger.warning("Disconnected from server.")
            return False
        msg = message_pb2.Message()
        msg.ParseFromString(data)
        handler = self.handlers.get(msg.type)
        if handler:
            handler(msg)
        else:
            self.logger.warning(f"No handler for msg type: {msg.type}")
        return True

    def wait_loop(self, stdin_handler):
        """等待消息并处理标准输入"""
        while True:
            try:
                readable, _, _ = select.select([self.sock, sys.stdin], [], [])
                for r in readable:
                    if r == self.sock:
                        if not self.receive_and_dispatch():
                            return
                    elif r == sys.stdin:
                        cmd = sys.stdin.readline().strip()
                        if cmd:
                            stdin_handler(cmd)
            except Exception as e:
                self.logger.error(f"Select error: {e}")
                break

