# Copyright (c) 2025 An Hongxu
# Peking University - School of Software and Microelectronics
# Email: anhongxu@stu.pku.edu.cn
#
# For academic use only. Commercial usage is prohibited without authorization.

import time
import hashlib
import message_pb2

from typing import List
from transaction import Transaction
from logger import setup_logger
from google.protobuf import json_format

logger = setup_logger('block')

class Block:
    def __init__(self, index: int, prev_hash: str, transactions: List[Transaction], validator: str, timestamp: float = None):
        self._proto = message_pb2.Block()
        self._proto.index = index
        self._proto.prev_hash = prev_hash
        self._proto.validator = validator
        self._proto.timestamp = timestamp if timestamp is not None else time.time()

        for tx in transactions:
            self._proto.transactions.append(tx.to_proto())

        # 自动计算并设置哈希
        self._proto.hash = self.compute_hash()
        logger.debug(f"Block created: {self.index}, hash: {self.hash[:8]}...")

    @property
    def index(self):
        return self._proto.index

    @property
    def prev_hash(self):
        return self._proto.prev_hash

    @property
    def hash(self):
        return self._proto.hash  # 只读属性

    @property
    def validator(self):
        return self._proto.validator

    @property
    def timestamp(self):
        return self._proto.timestamp

    @property
    def transactions(self):
        return [Transaction.from_proto(tx) for tx in self._proto.transactions]

    def compute_hash(self) -> str:
        """计算区块的哈希值"""  
        tx_str = "".join([f"{tx.sender}->{tx.receiver}:{tx.amount}@{tx.timestamp}" for tx in self.transactions])
        block_string = f"{self.index}{self.prev_hash}{self.timestamp}{self.validator}{tx_str}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_proto(self):
        return self._proto

    @staticmethod
    def from_proto(pb_block):
        block = Block(
            index=pb_block.index,
            prev_hash=pb_block.prev_hash,
            transactions=[Transaction.from_proto(tx) for tx in pb_block.transactions],
            validator=pb_block.validator,
            timestamp=pb_block.timestamp
        )
        # 注意：此处只使用已有 hash，不重新计算
        block._proto.hash = pb_block.hash
        return block

    def to_dict(self):
        return json_format.MessageToDict(self._proto, preserving_proto_field_name=True)

    @staticmethod
    def from_dict(data):
        pb_block = message_pb2.Block()
        json_format.ParseDict(data, pb_block)
        return Block.from_proto(pb_block)

    def __repr__(self):
        """简化的字符串表示，便于调试和日志记录"""
        return f"Block(index={self.index}, validator={self.validator}, txs={len(self.transactions)}, hash={self.hash[:8]}...)"

genesis_block = Block(
    index=0,
    prev_hash="0" * 64,  # 创世区块的前哈希为全零
    transactions=[],
    validator="genesis",
    timestamp=0  # 创世区块的时间戳为0
)
