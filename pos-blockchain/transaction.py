# Copyright (c) 2025 An Hongxu
# Peking University - School of Software and Microelectronics
# Email: anhongxu@stu.pku.edu.cn
#
# For academic use only. Commercial usage is prohibited without authorization.

import hashlib
import time
import message_pb2

from google.protobuf import json_format

class Transaction:
    def __init__(self, sender: str, receiver: str, amount: float, timestamp: float = None, tx_type=None):
        self._proto = message_pb2.Transaction()
        self._proto.sender = sender
        self._proto.receiver = receiver
        self._proto.amount = amount
        self._proto.timestamp = timestamp if timestamp is not None else time.time()
        if tx_type is not None:
            self._proto.type = tx_type

    @property
    def sender(self):
        return self._proto.sender

    @property
    def receiver(self):
        return self._proto.receiver

    @property
    def amount(self):
        return self._proto.amount

    @property
    def timestamp(self):
        return self._proto.timestamp

    @property
    def type(self):
        return self._proto.type

    @type.setter
    def type(self, value):
        self._proto.type = value

    def tx_id(self):
        """Generate a unique transaction ID based on the transaction details."""
        content = f"{self.sender}->{self.receiver}:{self.amount}@{self.timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()

    def to_proto(self):
        return self._proto

    @staticmethod
    def from_proto(pb_tx):
        tx = Transaction(
            sender=pb_tx.sender,
            receiver=pb_tx.receiver,
            amount=pb_tx.amount,
            timestamp=pb_tx.timestamp,
            tx_type=pb_tx.type,
        )
        return tx

    def to_dict(self):
        return json_format.MessageToDict(self._proto, preserving_proto_field_name=True)

    @staticmethod
    def from_dict(data):
        pb_tx = message_pb2.Transaction()
        json_format.ParseDict(data, pb_tx)
        return Transaction.from_proto(pb_tx)

    def __repr__(self):
        type_name = message_pb2.Transaction.TransactionType.Name(self.type)
        return f"Transaction({self.sender} -> {self.receiver}, {self.amount}, type={type_name})"

    def __eq__(self, other):
        if not isinstance(other, Transaction):
            return False
        return (
            self.sender == other.sender and
            self.receiver == other.receiver and
            abs(self.amount - other.amount) < 1e-9 and
            int(self.timestamp) == int(other.timestamp) and
            self.type == other.type
        )
