# PoS 区块链模拟项目完整梳理

## 项目概述

这是一个基于权益证明（Proof-of-Stake）共识机制的区块链模拟框架，由北京大学软件与微电子学院安鸿旭开发，专用于学术研究和教学演示。

### 核心特点
- **C/S 架构**：节点通过中心服务器转发消息，支持网络故障模拟
- **PoS 共识**：质押决定出块权重，支持可选投票确认机制
- **分叉处理**：支持链重组和 Nothing-at-Stake 攻击场景
- **自动同步**：新节点上线自动获取最新链状态
- **多种交易**：支持转账、质押、解质押三种交易类型
- **实验编排**：提供 YAML 配置的批量测试工具

## 项目结构

```
pos-blockchain/
├── 核心组件
│   ├── aserver.py           # 异步消息服务器
│   ├── node.py             # 区块链节点实现
│   ├── blockchain.py       # 区块链核心逻辑
│   ├── block.py            # 区块数据结构
│   ├── transaction.py      # 交易数据结构
│   ├── wallet_manager.py   # 钱包状态管理
│   └── client.py           # 客户端连接管理
├── 工具组件
│   ├── sim_orchestrator.py # 实验编排器
│   ├── timer.py            # 定时器工具
│   ├── logger.py           # 日志系统
│   ├── decorators.py       # 装饰器工具
│   └── utils.py            # 通用工具函数
├── 协议定义
│   ├── proto/message.proto # protobuf 消息定义
│   └── message_pb2.py      # 生成的 Python 消息类
├── 配置文件
│   ├── config.yaml         # 主配置文件
│   ├── sim_config/
│   │   ├── demo.yaml       # 基础演示配置
│   │   └── fork_demo.yaml  # 分叉测试配置
├── 测试工具
│   ├── check_blockchain.py # 一致性检查工具
│   └── timer_test.py       # 定时器测试
└── README.md              # 项目文档
```

## 核心组件详解

### 1. 服务器（aserver.py）

**功能**：作为消息中转中心，管理所有节点连接

**主要特性**：
- 异步 I/O 处理，支持大量并发连接
- 消息广播和转发机制
- 网络故障模拟（丢包、延迟）
- 自动 STEP 消息生成（可手动控制）

**支持的命令**：
```
step                    # 手动广播 STEP 消息
stop/continue          # 暂停/恢复自动 STEP
drop <node_id> on/off  # 模拟丢包
delay <node_id> <ms>   # 模拟网络延迟  
exit                   # 关闭服务器
help                   # 显示帮助信息
```

### 2. 节点（node.py）

**功能**：维护本地区块链状态，处理交易和区块

**核心功能模块**：
- 区块链状态管理
- 交易池维护
- 消息处理（使用装饰器模式）
- 投票机制（可选）
- 自动同步机制

**支持的命令**：
```
tx <to> <amount>       # 发送转账交易
stake <amount>         # 质押代币
unstake <amount>       # 解除质押
forge [--force]        # 出块（force 跳过验证者检查）
sync                   # 请求同步
chain                  # 显示区块链结构
wallet                 # 显示账户状态
mempool               # 显示待确认交易
info                  # 显示节点完整信息
nodes                 # 显示已知节点
exit                  # 退出节点
```

### 3. 区块链（blockchain.py）

**核心算法实现**：

**PoS 验证者选择**：
```python
def select_validator(self, known_validators: list):
    # 1. 收集质押大于0的候选者
    # 2. 如无质押者，使用余额权重
    # 3. 以当前 head 区块哈希作为随机种子
    # 4. 按权重随机选择验证者
```

**链重组机制**：
```python
def _reorganize_chain(self, new_head: Block):
    # 1. 找到公共祖先区块
    # 2. 构建新分支路径
    # 3. 重新计算钱包状态
    # 4. 触发重组回调（恢复被移除区块中的交易）
```

**区块验证**：
- 父区块存在性检查
- 区块高度连续性验证
- 哈希正确性验证
- 交易合法性验证（基于父区块状态）

### 4. 钱包管理（wallet_manager.py）

**账户数据结构**：
```python
{
    "账户ID": {
        "balance": float,  # 可用余额
        "stake": float     # 质押金额
    }
}
```

**核心操作**：
- `deposit/withdraw`：余额操作
- `stake_tokens/unstake_tokens`：质押操作
- `get_balance/get_stake`：状态查询
- `set_state/all_accounts`：状态同步

### 5. 消息协议（message.proto）

**消息类型**：
```protobuf
enum MessageType {
    HELLO = 0;          # 节点连接
    BYE = 1;            # 节点断开
    TRANSACTION = 2;    # 交易广播
    BLOCK = 3;          # 区块广播
    SYNC_REQUEST = 4;   # 同步请求
    SYNC_RESPONSE = 5;  # 同步响应
    STEP = 6;           # 出块信号
    BLOCK_VOTE = 7;     # 区块投票
}
```

**交易类型**：
```protobuf
enum TransactionType {
    TRANSFER = 0;       # 转账
    STAKE = 1;          # 质押
    UNSTAKE = 2;        # 解质押
}
```

## 实验编排器（sim_orchestrator.py）

### 功能特性
- **YAML 配置**：声明式实验定义
- **时间轴控制**：精确的事件调度
- **交互调试**：逐秒执行模式
- **进程管理**：自动启动/停止所有组件
- **日志系统**：独立的进程日志文件

### 配置结构
```yaml
# 全局配置
python_bin: python3           # Python 解释器
working_dir: .               # 工作目录
log_level: DEBUG             # 日志级别
log_file: experiment.log     # 日志文件

# 服务器配置
server:
  cmd: "{python} aserver.py"

# 节点配置
nodes:
  node1: { cmd: "{python} node.py --node node1" }
  node2: { cmd: "{python} node.py --node node2" }

# 清理配置
post_wait: 5                 # 实验结束等待时间
node_exit_wait: 5            # 节点退出等待时间

# 时间轴事件
timeline:
  - at: 0                    # 时间点（支持 5s, 1m30s 格式）
    target: server           # 目标（server 或节点ID）
    run: "stop"              # 命令（字符串或列表）
```

### 时间解析功能
支持多种时间格式：
- 纯数字：秒数
- 单位后缀：`5s`, `2m`, `1h`, `500ms`
- 组合格式：`1m30s`, `2h5m10s`

## 配置系统

### 主配置文件（config.yaml）

```yaml
# 服务器配置
server:
  host: "127.0.0.1"         # 监听地址
  port: 5000                # 监听端口

# 同步配置
sync:
  timeout: 2.0              # 同步超时时间

# 出块配置
step:
  interval: 5.0             # 自动STEP间隔

# 投票配置
vote:
  enabled: false            # 是否启用投票
  timeout: 5.0              # 投票超时
  threshold: 0.66           # 投票阈值（比例）

# 初始状态
initial_state:
  node1:
    balance: 100.0          # 初始余额
    stake: 0.0              # 初始质押
  node2:
    balance: 100.0
    stake: 0.0
```

## 核心算法流程

### 1. 出块流程
```
1. 接收 STEP 消息
2. 基于质押权重选择验证者
3. 如果是当前节点：
   a. 从交易池选择有效交易
   b. 创建新区块
   c. 广播区块消息
4. 如果启用投票：投票确认
5. 否则：直接加入链
```

### 2. 区块确认流程（投票模式）
```
1. 收到新区块
2. 验证区块有效性
3. 投票支持该区块
4. 临时存储等待其他投票
5. 投票达到阈值：加入主链
6. 投票超时：丢弃区块
```

### 3. 链同步流程
```
1. 节点启动时广播 SYNC_REQUEST
2. 其他节点响应 SYNC_RESPONSE（包含完整链）
3. 收集所有响应（超时2秒）
4. 选择最长链
5. 如果本地链较短：重组到新链
6. 恢复被移除区块中的交易到交易池
```

### 4. 分叉处理流程
```
1. 收到区块，父区块不是当前 head
2. 验证区块有效性
3. 如果新区块高度 > 当前链：
   a. 找到公共祖先
   b. 构建新链路径
   c. 重新计算状态
   d. 切换到新链
   e. 恢复被移除交易
4. 否则：仅存储不切换
```

## 网络故障模拟

### 丢包模拟
```bash
# 服务器命令
drop node1 on      # 开启 node1 丢包
drop node1 off     # 关闭 node1 丢包
drop node1 toggle  # 切换 node1 丢包状态
drop               # 显示当前丢包状态
```

### 延迟模拟
```bash
# 服务器命令
delay node1 500    # node1 延迟 500ms
delay node1 off    # 关闭 node1 延迟
delay              # 显示当前延迟状态
```

## 实验场景示例

### 1. 基础转账演示（demo.yaml）
```yaml
timeline:
  - at: 0
    target: server
    run: "stop"              # 停止自动出块
  - at: 4s
    target: node1
    run: "tx node2 10"       # node1 向 node2 转账
  - at: 5s
    target: server
    run: "step"              # 手动触发出块
  - at: 8s
    target: [node1, node2]
    run: "info"              # 查看状态
```

### 2. 分叉攻击演示（fork_demo.yaml）
```yaml
timeline:
  - at: 2s
    target: server
    run: "drop node2 on"     # 隔离 node2
  - at: 5s
    target: [node1, node2]
    run: "stake 10"          # 两节点都质押
  - at: 7s
    target: node1
    run: "forge --force"     # node1 出块
  - at: 8s
    target: node2
    run: "forge --force"     # node2 出块（同高度）
  - at: 10s
    target: node2
    run: ["tx node1 10", "forge --force"]  # node2 出更长链
  # node1 会切换到 node2 的更长链
```

## 数据持久化

### 区块链数据存储
- 位置：`data_node_{node_id}/blocks.json`
- 格式：JSON 数组，包含所有区块的序列化数据
- 加载：节点启动时自动加载，失败则创建新链

### 一致性检查
```bash
python check_blockchain.py  # 检查所有节点数据一致性
```

## 日志系统

### 日志配置
- **文件日志**：`logs/{component}.log`，按天轮转
- **控制台日志**：实时显示
- **调试日志**：DEBUG 模式下生成 `{component}.debug.log`

### 日志级别
- `INFO`：基本运行信息
- `DEBUG`：详细调试信息（包含节点输出）
- `WARNING`：警告信息
- `ERROR`：错误信息

## 扩展性设计

### 装饰器模式
```python
@command("tx", "tx <to> <amount> - transfer tokens")
def _cmd_tx(self, args):
    # 命令处理逻辑

@message_handler(message_pb2.Message.TRANSACTION)
def _on_transaction(self, msg):
    # 消息处理逻辑
```

### 回调机制
```python
# 注册链重组回调
blockchain.register_reorg_callback(self._on_reorg)

# 重组时自动调用
def _on_reorg(self, removed_blocks):
    # 恢复被移除区块中的交易
```

### 配置驱动
所有行为参数都可通过 `config.yaml` 调整，无需修改代码。

## 安全性考虑

### 交易验证
- 余额充足性检查
- 质押金额有效性验证
- 交易金额正数检查
- 重复交易过滤

### 区块验证
- 父区块存在性
- 区块哈希正确性
- 交易集合有效性
- 验证者权限检查

### 投票机制
- 验证者身份检查（质押 > 0）
- 投票阈值验证
- 超时处理
- 重复投票过滤

## 性能特性

### 异步处理
- 服务器使用 asyncio，支持高并发
- 非阻塞消息传输
- 异步延迟发送

### 内存管理
- 区块哈希索引加速查找
- 临时状态的及时清理
- 深拷贝避免状态污染

### 时间复杂度
- 区块查找：O(1)
- 链重组：O(n)，n为分叉长度
- 交易验证：O(m)，m为交易数量

## 局限性说明

1. **网络模型**：星型拓扑，实际区块链为 P2P 网络
2. **共识简化**：未实现完整的 PoS 惩罚机制
3. **安全性**：无密码学签名验证
4. **扩展性**：单机模拟，无真实分布式特性
5. **性能**：未优化大规模场景

## 总结

这是一个功能完整的 PoS 区块链模拟器，特别适合：

- **教学演示**：直观展示区块链核心概念
- **算法研究**：测试共识算法和分叉处理
- **故障模拟**：网络分区、节点失效等场景
- **性能测试**：不同参数下的系统行为

通过 YAML 配置和交互式调试功能，研究者可以方便地设计和执行各种区块链实验场景。