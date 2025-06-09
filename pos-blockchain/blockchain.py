# Copyright (c) 2025 An Hongxu
# Peking University - School of Software and Microelectronics
# Email: anhongxu@stu.pku.edu.cn
#
# For academic use only. Commercial usage is prohibited without authorization.

import random
import hashlib
import json
import copy
import os
import message_pb2

from block import Block, genesis_block
from logger import setup_logger
from wallet_manager import WalletManager
from utils import load_config

logger = setup_logger("blockchain")

class Blockchain:
    def __init__(self):
        """
        Blockchain对象初始化：创建创世区块并设置初始账户余额状态。
        """
        self.blocks_by_hash = {} # block_hash -> Block
        self.chain = [] 

        # 用于处理账户余额和交易
        initial_state = load_config(section="initial_state") 
        self.wallet = WalletManager()
        self.wallet.set_state(initial_state)  # 初始化钱包状态为创世初始状态 

        # 保存创世初始状态，以便重算或验证使用
        self.genesis_state = copy.deepcopy(initial_state)

        # 创世区块
        self.chain.append(genesis_block)
        self.blocks_by_hash[genesis_block.hash] = genesis_block

        # 重组移除的区块暂存: 用于通知节点恢复其中交易
        self.reorg_removed = None

        # 重组回调列表：用于通知订阅者链重组事件 
        self.reorg_callbacks = []

    @property
    def head(self) -> Block:
        """返回当前主链最后一个区块（最新区块）。"""
        return self.chain[-1] if self.chain else None

    def register_reorg_callback(self, callback):
        """注册重组回调函数，当发生链重组时调用。"""
        self.reorg_callbacks.append(callback)

    def balance(self, account_id: str) -> float:
        """获取指定账户的余额。"""
        return self.wallet.get_balance(account_id)

    def stake(self, account_id: str) -> float:
        """获取指定账户的质押金额。"""
        return self.wallet.get_stake(account_id)

    def get_wallet_info(self) -> dict:
        """获取当前钱包状态的所有账户信息，包括余额和质押金额。"""
        return self.wallet.all_accounts()

    def validate_block(self, block: Block) -> bool:
        """验证新区块的正确性，在未改变状态的情况下进行检查。"""
        # 创世区块校验
        if block.index == 0:
            # 比较创世区块哈希是否一致
            return block.hash == self.chain[0].hash

        # 父区块必须已知
        parent = self.blocks_by_hash.get(block.prev_hash)
        if parent is None:
            logger.error(f"validate_block: Unknown parent {block.prev_hash}")
            return False

        # 校验区块高度连续
        if block.index != parent.index + 1:
            logger.error(f"validate_block: Invalid index {block.index} (expected {parent.index+1})")
            return False

        # 校验区块哈希正确性
        if block.compute_hash() != block.hash:
            logger.error(f"validate_block: Block hash mismatch for index {block.index}")
            return False

        # 验证区块内交易合法性：需基于区块父节点时刻的状态
        # 首先确定父区块对应的状态（如果父区块在主链，则状态即当前state；如果在分叉上，则需要重演至父区块）
        if parent.hash == self.head.hash:
            # 父块是当前主链末端，直接使用当前状态的拷贝
            temp_wallet = copy.deepcopy(self.wallet)
        else:
            # 父块在某个分叉上，需计算该父块所在链的状态
            temp_wallet = WalletManager()
            temp_state = copy.deepcopy(self.genesis_state)  # 从创世状态开始
            temp_wallet.set_state(temp_state)
            # 找到从创世到父块的链路径
            branch_blocks = []
            cur = parent
            while cur.index != 0:
                branch_blocks.append(cur)
                cur = self.blocks_by_hash[cur.prev_hash]
            branch_blocks.reverse()
            for b in branch_blocks:
                if not self._apply_block_to_wallet(temp_wallet, b, validate_only=True):
                    logger.error(f"validate_block: Failed to apply block {b.index} for state validation")
                    return False

        return self._apply_block_to_wallet(temp_wallet, block, validate_only=True)

    def _apply_block_to_wallet(self, wallet: WalletManager, block: Block, validate_only: bool = False) -> bool:
        """应用区块到钱包状态，验证交易合法性。"""
        for tx in block.transactions:
            # check
            if tx.amount <= 0:
                return False
            if (tx.type == message_pb2.Transaction.TRANSFER or tx.type == message_pb2.Transaction.STAKE) and wallet.get_balance(tx.sender) < tx.amount:
                return False
            if tx.type == message_pb2.Transaction.UNSTAKE and wallet.get_stake(tx.sender) < tx.amount:
                return False

            # 根据交易类型处理
            if not validate_only:
                if tx.type == message_pb2.Transaction.TRANSFER:
                    wallet.withdraw(tx.sender, tx.amount)
                    wallet.deposit(tx.receiver, tx.amount)
                elif tx.type == message_pb2.Transaction.STAKE:
                    if not wallet.stake_tokens(tx.sender, tx.amount):
                        logger.error(f"Failed to stake tokens for {tx.sender}")
                        return False
                elif tx.type == message_pb2.Transaction.UNSTAKE:
                    if not wallet.unstake_tokens(tx.sender, tx.amount):
                        logger.error(f"Failed to unstake tokens for {tx.sender}")
                        return False
        return True

    def add_block(self, block: Block):
        """将区块添加到区块链。如区块有效则更新链和状态；若出现分叉则处理最长链切换。"""
        if not self.validate_block(block):
            raise Exception(f"Block {block.index} failed validation")
        # 先将区块加入全局哈希索引存储
        self.blocks_by_hash[block.hash] = block

        if block.prev_hash == self.head.hash:
            # 1. 区块直接连接在当前主链末端
            logger.info(f"Adding block {block.index} to main chain")
            self._apply_block_to_wallet(self.wallet, block, validate_only=False)  # 更新钱包状态
            self.chain.append(block)  # 更新主链
        else:
            # 2. 区块属于某分叉
            logger.info(f"Block {block.index} is a fork (prev_hash={block.prev_hash[:8]})")
            if block.index > self.head.index:
                logger.info(f"New block {block.index} is longer than current head {self.head.index}, reorganizing chain")
                # 新区块高度超过当前主链，触发链重组切换到更长链
                self._reorganize_chain(block)
            else:
                logger.info(f"Block {block.index} is shorter than current head {self.head.index}, not switching")
                # 区块在更短的链上，只存储不切换（可能用于以后分叉延长）
                pass

    def _reorganize_chain(self, new_head: Block):
        """处理链重组逻辑，将新头区块的分支合并到主链上。"""
        main_chain_hashes = {b.hash for b in self.chain}
        new_branch = []
        cur = new_head
        while cur and cur.hash not in main_chain_hashes:
            new_branch.append(cur)
            cur = self.blocks_by_hash.get(cur.prev_hash)
        common_ancestor = cur if cur else self.chain[0]
        new_branch.reverse()
        new_chain = self.chain[:common_ancestor.index + 1] + new_branch
        self._apply_reorg(new_chain, common_ancestor)

    def reorganize_to_chain(self, new_chain):
        """将当前链重组为提供的新链。新链必须包含当前主链的某个祖先区块。"""
        if not new_chain:
            logger.warning("Empty chain provided to reorganize_to_chain")
            return
        common_ancestor = None
        for blk in reversed(self.chain):
            if blk.hash in {b.hash for b in new_chain}:
                common_ancestor = blk
                break
        if common_ancestor is None:
            logger.info("No common ancestor found in reorganize_to_chain")
            return
        self._apply_reorg(new_chain, common_ancestor)

    def _apply_reorg(self, new_chain, common_ancestor):
        """应用链重组逻辑，将新链合并到当前链上。"""
        ca_index = common_ancestor.index
        old_chain = list(self.chain)
        removed_blocks = old_chain[ca_index + 1:]

        new_wallet = WalletManager()
        new_wallet.set_state(copy.deepcopy(self.genesis_state))

        for blk in new_chain[1:]:  # skip genesis
            if not self._apply_block_to_wallet(new_wallet, blk, validate_only=False):
                raise Exception("Reorganize failed: invalid block in new chain")

        self.chain = new_chain
        self.blocks_by_hash = {blk.hash: blk for blk in new_chain}
        self.wallet = new_wallet
        self.reorg_removed = removed_blocks

        logger.info(f"Reorganized chain: new head {new_chain[-1].hash[:8]} height {new_chain[-1].index}")
        for callback in self.reorg_callbacks:
            callback(removed_blocks)

    def select_validator(self, known_validators: list):
        """根据主链 head 区块 hash 作为 randomness seed，保证各节点 deterministic 选 validator"""
        accounts = self.get_wallet_info()
        candidates = []
        weights = []

        for account_id, info in accounts.items():
            if account_id not in known_validators:
                continue
            stake = info.get("stake", 0)
            if stake > 0:
                candidates.append(account_id)
                weights.append(stake)

        if not candidates:
            # fallback: use balance weights instead
            logger.warning("No validators with stake > 0, fallback to balance-weighted selection.")

            for account_id, info in accounts.items():
                if account_id not in known_validators:
                    continue
                balance = info.get("balance", 0)
                if balance > 0:
                    candidates.append(account_id)
                    weights.append(balance)

        if not candidates:
            logger.error("No validators available at all (stake=0 and balance=0)")
            return None

        # 以 head 区块 hash 作为 seed
        head_hash = self.head.hash
        seed_bytes = hashlib.sha256(head_hash.encode()).digest()
        seed_int = int.from_bytes(seed_bytes, byteorder="big")
        random.seed(seed_int)

        selected = random.choices(candidates, weights=weights, k=1)[0]
        logger.info(
            f"Selected validator for next block (based on head hash {head_hash[:8]}...): {selected} "
            f"(stake weights={dict(zip(candidates, weights))})"
        )
        return selected

    def save_to_files(self, directory: str):
        """将当前区块链保存到指定目录下的JSON文件。"""
        os.makedirs(directory, exist_ok=True)
        # 保存区块链
        with open(f"{directory}/blocks.json", "w") as f:
            json.dump([blk.to_dict() for blk in self.chain], f, indent=2)
        logger.info(f"Blockchain saved to {directory}")

    def load_from_files(self, directory: str):
        """从指定目录加载区块链数据，重建钱包状态。"""
        try:
            with open(f"{directory}/blocks.json", "r") as f:
                blocks_data = json.load(f)
            chain = []
            blocks_by_hash = {}
            for blk_data in blocks_data:
                blk = Block.from_dict(blk_data)
                chain.append(blk)
                blocks_by_hash[blk.hash] = blk

            # 重建钱包
            new_wallet = WalletManager()
            new_wallet.set_state(copy.deepcopy(self.genesis_state))
            for blk in chain[1:]:  # skip genesis
                if not self._apply_block_to_wallet(new_wallet, blk, validate_only=False):
                    raise Exception("load_from_files failed: invalid block")

            self.chain = chain
            self.blocks_by_hash = blocks_by_hash
            self.wallet = new_wallet
            logger.info(f"Blockchain loaded successfully from {directory}. Chain length={len(chain)-1}")
            return True
        except FileNotFoundError:
            return False
