# Copyright (c) 2025 An Hongxu
# Peking University - School of Software and Microelectronics
# Email: anhongxu@stu.pku.edu.cn
#
# For academic use only. Commercial usage is prohibited without authorization.

import sys
import os
import argparse
import message_pb2

from blockchain import Blockchain
from block import Block
from transaction import Transaction
from utils import load_config
from client import Client
from logger import setup_logger
from decorators import command, message_handler
from timer import Timer

class Node:
    def __init__(self, node_id: str):
        self.id = node_id
        self.logger = setup_logger(node_id)

        # 创建数据目录
        self.data_dir = f"data_node_{self.id}"
        os.makedirs(self.data_dir, exist_ok=True)

        # 注册命令
        self.commands = {}
        self._register_commands()

        # for sync
        sync_config = load_config(section="sync")
        self.sync_responses = []                                    # pending sync responses
        self.sync_in_progress = False                               # whether in sync process
        self.sync_timeout = sync_config.get('timeout', 2.0)         # sync timeout, seconds

        # for vote
        vote_config = load_config(section="vote")
        self.use_voting = vote_config.get('enabled', False)         # whether to use voting, default False
        self.pending_block_votes = {}                               # block_hash -> voter_id
        self.pending_blocks = {}                                    # block_hash -> Block 对象
        self.vote_timeout = vote_config.get('timeout', 5.0)         # vote timeout, seconds
        self.vote_threshold = vote_config.get('threshold', 0.66)    # vote threshold, of online validators
        self.known_nodes = set()                                    # known nodes set
        self.known_nodes.add(self.id)

        # 初始化或加载区块链
        if os.path.exists(os.path.join(self.data_dir, "blocks.json")):
            self.blockchain = Blockchain()
            success = self.blockchain.load_from_files(self.data_dir)
            if not success:
                self.logger.error(f"Failed to load blockchain data, starting new.")
                self.blockchain = Blockchain()
        else:
            self.blockchain = Blockchain()


        # 订阅重组事件
        # 当链重组时，恢复未确认交易池中的交易
        self.blockchain.register_reorg_callback(self._on_reorg)

        # 未确认交易池
        self.mempool = []

        # 启动 Client
        server_config = load_config(section="server")
        server_host = server_config.get('host', 'localhost')
        server_port = server_config.get('port', 5000)
        self.client = Client(node_id, server_host, server_port, self.logger)
        self.client.register_handlers(self)    # register message handlers

        # 从系统中同步链
        self.request_sync()


        self.logger.info(f"Node {self.id} started. Connected to server at {server_host}:{server_port}.")
        self.logger.info(f"Current chain length: {len(self.blockchain.chain) - 1} (excluding genesis)")

    def run(self):
        self.client.wait_loop(self._on_command)

    def _register_commands(self):
        """注册命令到 commands 字典中"""
        for attr in dir(self):
            method = getattr(self, attr)
            if callable(method) and hasattr(method, "_is_command"):
                name = method._command_name
                help_text = method._help_text
                self.commands[name] = {"func": method, "help": help_text}

    @message_handler(message_pb2.Message.HELLO)
    def _on_hello(self, msg):
        """处理 HELLO 消息，记录新节点 ID"""
        self.logger.info(f"Received HELLO message from node {msg.sender_id}.")
        self.known_nodes.add(msg.sender_id)

    @message_handler(message_pb2.Message.BYE)
    def _on_bye(self, msg):
        """处理 BYE 消息，移除已知节点"""
        self.logger.info(f"Received BYE message from node {msg.sender_id}.")
        if msg.sender_id == "server":
            self.logger.info("Server is shutting down, exiting.")
            self._cmd_exit(0)
        if msg.sender_id in self.known_nodes:
            self.known_nodes.remove(msg.sender_id)

    @message_handler(message_pb2.Message.STEP)
    def _on_step(self, msg):
        """处理 STEP 消息，尝试forge新区块"""
        self.logger.info("Received STEP message, attempting to forge block...")
        self.forge_block()

    def _vote(self, block: Block):
        """投票同意新区块"""
        vote_msg = message_pb2.Message(
            type=message_pb2.Message.BLOCK_VOTE,
            sender_id=self.id,
            block_vote=message_pb2.BlockVote(
                voter_id=self.id,
                block_hash=block.hash,
            )
        )
        self.client.send(vote_msg)
        self.logger.info(f"Voted to accept Block {block.index}, hash={block.hash[:8]}")

    def _stash_block(self, block: Block):
        """临时保存未确认区块，等待投票完成后再加入链"""
        if block.hash not in self.pending_blocks:
            self.pending_block_votes[block.hash] = set()

        self.pending_blocks[block.hash] = block

        if self.blockchain.stake(self.id) > 0:
            self.pending_block_votes[block.hash].add(self.id)

    def _add_block(self, block: Block):
        """添加区块到链上"""
        try:
            self.blockchain.add_block(block)
            self.logger.info(f"Added new block {block.index} with hash {block.hash[:8]}. Chain length is now {len(self.blockchain.chain)-1}(excluding genesis).")
        except Exception as e:
            self.logger.error(f"Failed to add block {block.index}: {e}")
            return

        # 从未确认交易池中移除已包含在区块中的交易
        for tx in block.transactions:
            if tx in self.mempool:
                self.mempool.remove(tx)

    @message_handler(message_pb2.Message.BLOCK)
    def _on_block(self, msg):
        block = Block.from_proto(msg.block)

        # 检查区块是否已存在
        if block.hash in self.blockchain.blocks_by_hash:
            return


        if self.use_voting:
            # 验证 block 是否合法
            if not self.blockchain.validate_block(block):
                self.logger.warning(f"Block {block.index} failed validation, rejecting.")
                return

            # 开启投票验证流程
            self._vote(block)
            self._stash_block(block)
            # 开启timer检查投票超时
            Timer(self.vote_timeout, self._check_vote_timeout, 1, block.hash).start()
        else:
            # 关闭投票，直接加链
            self.logger.info(f"[No Voting] Directly adding Block {block.index} from {block.validator} ...")
            self._add_block(block)
            self.logger.info(f"[No Voting] added block {block.index}. Chain length is now {len(self.blockchain.chain)-1}(excluding genesis).")

    @message_handler(message_pb2.Message.BLOCK_VOTE)
    def _on_block_vote(self, msg):
        """处理 BLOCK_VOTE 消息，检查投票是否达到阈值"""
        # 未在 pending_blocks 中忽略
        if msg.block_vote.block_hash not in self.pending_blocks:
            self.logger.info(f"Received BLOCK VOTE message from {msg.sender_id} on block {msg.block_vote.block_hash[:8]}. Not in pending blocks, Ignoring.")
            return

        # 非验证者节点投票忽略
        if self.blockchain.stake(msg.sender_id) <= 0:
            self.logger.warning(f"Received BLOCK VOTE from {msg.sender_id} on block {msg.block_vote.block_hash[:8]}. Not validator node, Ignoring")
            return

        vote = msg.block_vote
        block_hash = vote.block_hash
        voter_id = vote.voter_id

        self.logger.info(f"Received BLOCK_VOTE from {voter_id} on block {block_hash[:8]}")

        # 记录投票节点
        self.pending_block_votes[block_hash].add(voter_id)

        def get_online_validator_count(node_ids):
            """计算在线验证者数量"""
            cnt = 0
            for node_id in node_ids:
                if self.blockchain.stake(node_id) > 0:
                    cnt += 1
            return max(cnt, 1) # 至少是1

        # 检查是否达到阈值
        total_known = get_online_validator_count(self.known_nodes)
        votes = len(self.pending_block_votes[block_hash])
        vote_ratio = votes / total_known

        self.logger.info(f"Block {block_hash[:8]} vote ratio: {vote_ratio:.2f}({votes}/{total_known})")

        # 如果投票比例达到阈值，验证区块并添加到链上
        if vote_ratio >= self.vote_threshold:
            if block_hash in self.pending_blocks:
                block = self.pending_blocks[block_hash]
                self.logger.info(f"Validated Block {block.index} from {block.validator}, processing...")
                self._add_block(block)
                self.logger.info(f"added new block. Chain length is now {len(self.blockchain.chain)-1}(excluding genesis).")

                # 清理状态
                del self.pending_block_votes[block_hash]
                del self.pending_blocks[block_hash]

    @message_handler(message_pb2.Message.TRANSACTION)
    def _on_transaction(self, msg):
        """处理交易消息，验证并添加到交易池"""
        tx = Transaction.from_proto(msg.tx)

        if tx.sender == self.id:
            return

        # 检查是否余额不足
        balance = self.blockchain.balance(tx.sender)
        stake = self.blockchain.stake(tx.sender)

        if tx.amount <= 0:
            self.logger.warning(f"rejected TX from {tx.sender}: invalid amount {tx.amount}.")
            return

        if tx.type == message_pb2.Transaction.TRANSFER:
            if balance < tx.amount:
                self.logger.warning(f"rejected TRANSFER TX from {tx.sender}: insufficient balance.")
                return
            self.logger.info(f"received TRANSFER: {tx.sender} → {tx.receiver}, amount {tx.amount}")

        elif tx.type == message_pb2.Transaction.STAKE:
            if balance < tx.amount:
                self.logger.warning(f"rejected STAKE TX from {tx.sender}: insufficient balance.")
                return
            self.logger.info(f"received STAKE: {tx.sender} stakes {tx.amount}")

        elif tx.type == message_pb2.Transaction.UNSTAKE:
            if stake < tx.amount:
                self.logger.warning(f"rejected UNSTAKE TX from {tx.sender}: insufficient stake.")
                return
            self.logger.info(f"received UNSTAKE: {tx.sender} unstakes {tx.amount}")

        else:
            self.logger.warning(f"unknown transaction type {tx.type} from {tx.sender}")
            return

        # 去重后加入交易池
        if tx not in self.mempool:
            self.mempool.append(tx)

    @message_handler(message_pb2.Message.SYNC_REQUEST)
    def _on_sync_request(self, msg):
        """处理 SYNC_REQUEST 消息，发送区块链"""
        self.logger.info(f"Received SYNC_REQUEST from {msg.sender_id}, sending SYNC_RESPONSE")
        # Prepare response
        sync_msg = message_pb2.Message(
            type=message_pb2.Message.SYNC_RESPONSE,
            sender_id=self.id,
            sync_response=message_pb2.SyncResponse()
        )
        # Add blocks
        for blk in self.blockchain.chain:
            sync_msg.sync_response.blocks.append(blk.to_proto())

        self.client.send(sync_msg)

    @message_handler(message_pb2.Message.SYNC_RESPONSE)
    def _on_sync_response(self, msg):
        """处理 SYNC_RESPONSE 消息，存储同步响应"""
        # 如果未知节点，添加到 known_nodes
        self.known_nodes.add(msg.sender_id)

        if not self.sync_in_progress:
            self.logger.warning("Received SYNC_RESPONSE but no sync in progress. Ignoring.")
            return

        self.logger.info(f"Received SYNC_RESPONSE from {msg.sender_id}, storing response")

        # Store the response
        blocks = [Block.from_proto(pb_blk) for pb_blk in msg.sync_response.blocks]

        self.sync_responses.append({
            "sender_id": msg.sender_id,
            "blocks": blocks,
        })

    def _on_reorg(self, removed_blocks):
        """处理链重组事件：从被移除区块中恢复未确认交易。当发生链重组时自动触发"""
        # 收集新链已确认的交易
        confirmed_tx_ids = {
            tx.tx_id()
            for blk in self.blockchain.chain
            for tx in blk.transactions
        }

        for blk in removed_blocks:
            for tx in blk.transactions:
                if tx.tx_id() not in confirmed_tx_ids:
                    self.mempool.append(tx)
                    self.logger.info(f"Recovered TX: {tx}")

    def _on_command(self, cmd: str):
        """处理用户输入的命令"""
        parts = cmd.strip().split()
        if not parts:
            return
        name = parts[0]
        args = parts[1:]
        command = self.commands.get(name)
        if command:
            try:
                command["func"](args)
            except Exception as e:
                self.logger.error(f"error executing '{name}': {e}")
        else:
            self.logger.warning(f"unknown command: {name}. Type 'help' for available commands.")

    def _check_vote_timeout(self, block_hash):
        """检查投票超时，清理未完成的投票状态"""
        try:
            # 检查是否有未完成投票的区块 
            if block_hash in self.pending_blocks:
                self.logger.warning(f"Vote timeout for block {block_hash[:8]}, discarding pending         state.")
                del self.pending_blocks[block_hash]
                if block_hash in self.pending_block_votes:
                    del self.pending_block_votes[block_hash]
        except Exception as e:
            self.logger.error(f"Vote timeout checker error: {e}")

    def _select_longest_chain(self):
        """从所有同步消息中，选出最长链"""
        # 选最长链
        best_chain = None
        best_length = -1

        for response in self.sync_responses:
            length = len(response["blocks"])
            chain_head = response["blocks"][-1].hash if response["blocks"] else "None"
            self.logger.info(f"SYNC_RESPONSE from {response['sender_id']}: chain length={length}     head={chain_head[:8]}")

            if length > best_length:
                best_length = length
                best_chain = response["blocks"]
        
        return best_chain

    def _process_sync_responses(self):
        """处理所有 SYNC_RESPONSE 消息，选出最优链, 当超时后自动调用"""
        self.logger.info("SYNC_RESPONSE collection finished. Processing responses.")
        self.sync_in_progress = False
        if not self.sync_responses:
            self.logger.warning("No SYNC_RESPONSE received. Sync failed.")
            return

        # 选出最长链
        # TODO(add more strategies, e.g. select chain with most stake?)
        best_chain = self._select_longest_chain()
        best_length = len(best_chain)

        # 本地链信息
        local_chain = self.blockchain.chain

        local_chain_hashes = [blk.hash for blk in local_chain]
        best_chain_hashes = [blk.hash for blk in best_chain]

        # 如果本地链和sync链一致 直接返回
        if local_chain_hashes == best_chain_hashes:
            self.logger.info(f'no need to sync chain, best chain same with local chain')
            return

        self.blockchain.reorganize_to_chain(best_chain)

    def request_sync(self):
        """请求同步区块链状态"""
        self.sync_responses = []
        self.sync_in_progress = True
        msg = message_pb2.Message(
            type=message_pb2.Message.SYNC_REQUEST,
            sender_id=self.id
        )
        self.client.send(msg)
        self.logger.info("Sent SYNC_REQUEST to network")
        # 指定时间后处理响应
        Timer(self.sync_timeout, self._process_sync_responses).start()

    def create_transaction(self, receiver: str, amount: float, tx_type=message_pb2.Transaction.TRANSFER):
        """创建并发送交易"""
        sender = self.id

        # 检查交易参数
        if sender == receiver and tx_type == message_pb2.Transaction.TRANSFER:
            self.logger.warning(f"attempted to send transaction to itself.")
            return


        # 创建交易对象
        tx = Transaction(sender, receiver, amount, tx_type=tx_type)

        if not self._validate_transaction(tx):
            self.logger.warning(f"Invalid transaction: {tx}")
            return

        self.mempool.append(tx)

        # 广播交易
        msg = message_pb2.Message(
            type=message_pb2.Message.TRANSACTION,
            sender_id=self.id,
            tx=tx.to_proto()
        )
        self.client.send(msg)
        self.logger.info(f"sent {message_pb2.Transaction.TransactionType.Name(tx_type)} transaction: {sender} -> {receiver} {amount}")

    def _validate_transaction(self, tx: Transaction):
        """验证交易是否有效"""
        balance = self.blockchain.balance(tx.sender)
        if tx.type == message_pb2.Transaction.TRANSFER:
            if balance < tx.amount:
                self.logger.warning(f"Transaction from {tx.sender} to {tx.receiver} with amount {tx.amount} is invalid due to insufficient balance.")
                return False
        elif tx.type == message_pb2.Transaction.STAKE:
            if balance < tx.amount:
                self.logger.warning(f"Stake transaction from {tx.sender} with amount {tx.amount} is invalid due to insufficient balance.")
                return False
        elif tx.type == message_pb2.Transaction.UNSTAKE:
            stake = self.blockchain.stake(tx.sender)
            if stake < tx.amount:
                self.logger.warning(f"Unstake transaction from {tx.sender} with amount {tx.amount} is invalid due to insufficient staked tokens.")
                return False
        return True

    def _pack_transactions(self):
        """将未确认交易池中的交易打包成区块"""
        if not self.mempool:
            self.logger.info("No transactions to pack into block.")
            return []

        # 只打包有效的交易
        valid_txs = []
        for tx in self.mempool:
            if self._validate_transaction(tx):
                valid_txs.append(tx)

        if not valid_txs:
            self.logger.info("No valid transactions to pack into block.")
            return []

        return valid_txs

    def forge_block(self, force=False):
        """尝试创建新区块并广播"""
        # force 参数用于跳过验证者检查 - for debug and test
        if not force:
            selected_validator = self.blockchain.select_validator(self.known_nodes)
            if selected_validator != self.id:
                self.logger.info(
                    f"Current node ({self.id}) is not selected to forge this block "
                    f"(selected validator={selected_validator})"
                )
                return
        else:
            self.logger.warning("FORCING block forge -- skipping validator check!")

        packaged_txs = self._pack_transactions()
        if not packaged_txs:
            return 

        prev = self.blockchain.head
        block = Block(
            index=prev.index + 1,
            prev_hash=prev.hash,
            validator=self.id,
            transactions=packaged_txs,
        )


        # 发送区块消息
        msg = message_pb2.Message(type=message_pb2.Message.BLOCK, sender_id=self.id, block=block.to_proto())
        self.client.send(msg)
        self.logger.info(f"Want to forge block {block.index} with hash {block.hash[:8]}")

        if self.use_voting:
            # 投票模式
            # 验证区块合法性
            if not self.blockchain.validate_block(block):
                self.logger.warning(f"Block {block.index} failed validation, rejecting.")
                return
            self._vote(block)
            self._stash_block(block)
            Timer(self.vote_timeout, self._check_vote_timeout, 1, block.hash).start()
        else:
            # 非投票模式，直接本地加链
            self.logger.info(f"[No Voting] Directly adding forged Block {block.index} ...")
            self._add_block(block)
            self.logger.info(f"[No Voting] forged block {block.index}. Chain length is now {len(self.blockchain.chain)-1}(excluding genesis).")

    def stake(self, amount: float):
        self.create_transaction(
            receiver=self.id,
            amount=amount,
            tx_type=message_pb2.Transaction.STAKE
        )

    def unstake(self, amount: float):
        self.create_transaction(
            receiver=self.id,
            amount=amount,
            tx_type=message_pb2.Transaction.UNSTAKE
        )

    @command("sync", "request blockchain sync from other nodes")
    def _cmd_sync(self, args):
        self.request_sync()

    @command("nodes", "get known nodes")
    def _cmd_nodes(self, args):
        print(f"Known nodes: {self.known_nodes}")

    @command("tx", "tx <to> <amount> - transfer tokens")
    def _cmd_tx(self, args):
        if len(args) != 2:
            print("usage: tx <to> <amount>")
            return
        to, amount = args
        self.create_transaction(to, float(amount))

    @command("forge", "forge a new block (use --force to bypass validator check)")
    def _cmd_forge(self, args):
        force = False
        if args and args[0] == "--force":
            force = True
        self.forge_block(force=force)

    @command("exit", "exit the program")
    def _cmd_exit(self, args):
        self.logger.info("Exiting.")
        self.blockchain.save_to_files(self.data_dir)
        sys.exit(0)

    @command("help", "show this help message")
    def _cmd_help(self, args):
        print("Available commands:")
        for name, info in self.commands.items():
            print(f"  {name.ljust(10)} - {info['help']}")

    @command("stake", "stake <amount> - stake tokens to participate in block validation")
    def _cmd_stake(self, args):
        if len(args) != 1:
            print("usage: stake <amount>")
            return
        amt = float(args[0])
        if self.blockchain.balance(self.id) >= amt:
            self.stake(amt)
            self.logger.info(f"Want to stake {amt} tokens.")
        else:
            self.logger.warning("Insufficient balance to stake.")

    @command("unstake", "unstake <amount> - unstake tokens")
    def _cmd_unstake(self, args):
        if len(args) != 1:
            print("usage: unstake <amount>")
            return
        amt = float(args[0])
        if self.blockchain.stake(self.id) >= amt:
            self.unstake(amt)
            self.logger.info(f"Want to unstaked {amt} tokens.")
        else:
            self.logger.warning("Insufficient staked balance to unstake.")

    @command("chain", "print blockchain")
    def _cmd_chain(self, args):
        print("========== Blockchain Structure ==========")
        # Build parent -> children mapping
        parent_to_children = {}
        for blk in self.blockchain.blocks_by_hash.values():
            parent_to_children.setdefault(blk.prev_hash, []).append(blk)

        for children in parent_to_children.values():
            children.sort(key=lambda b: b.index)

        def print_chain_recursively(block, prefix="", is_main_chain=True):
            marker = "(main)" if is_main_chain else "(fork)"
            print(
                f"{prefix}Block {block.index} | hash={block.hash[:8]}... "
                f"| validator={block.validator} | tx_count={len(block.transactions)} {marker}"
            )
            children = parent_to_children.get(block.hash, [])
            for i, child in enumerate(children):
                is_last = (i == len(children) - 1)
                branch_prefix = prefix + ("└── " if is_last else "├── ")
                print_chain_recursively(child, prefix=branch_prefix, is_main_chain=(child in self.blockchain.chain))

        genesis = self.blockchain.chain[0]
        print_chain_recursively(genesis)

        print("===================================")

    @command("wallet", "show wallet info")
    def _cmd_wallet(self, args):
        print("========== Account State ==========")
        accounts = self.blockchain.get_wallet_info()
        for account, info in accounts.items():
            balance = info.get("balance", 0)
            stake = info.get("stake", 0)
            print(
                f" Account {account} | Balance={balance:.2f} | Stake={stake:.2f}"
            )
        print("===================================")

    @command("mempool", "show pending transactions")
    def _cmd_mempool(self, args):
        print("========== Pending Transactions ==========")
        for tx in self.mempool:
            print(f"  {str(tx)}")
        print("==========================================")
    
    @command("info", "show current node info")
    def _cmd_info(self, args):
        print(f"Node ID: {self.id}")
        self._cmd_nodes(args)
        self._cmd_chain(args)
        self._cmd_wallet(args)
        self._cmd_mempool(args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blockchain Node")
    parser.add_argument("--node", help="Node ID (e.g., node1, node2, ...)", required=True)
    args = parser.parse_args()
    node = Node(args.node)
    node.run()
