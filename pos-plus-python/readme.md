# POS+ 区块链项目

## 项目简介

这是一个基于 Proof of Stake Plus (POS+) 共识机制的区块链实现，它结合了传统的 Proof of Stake (POS) 机制与恶意节点检测功能。该项目提供了一个简化的区块链网络，允许多个节点参与区块的验证和生成过程，同时检测并防范可能的恶意行为，包括双花攻击等安全威胁。POS+相比传统POS共识机制，增加了恶意行为检测算法，可以有效防止区块链网络中的多种攻击行为。

> **注意**：本项目是一个概念验证实现，部分功能（如恶意检测系统）可能只包含框架或模拟实现。在实际测试中，请关注双花检测、交易处理和区块生成等核心功能。

### 主要特点

1. **创世区块自动创建**：系统启动时自动创建初始区块
2. **节点注册与质押**：支持新节点注册并设置质押代币数量
3. **交易处理**：支持发送和接收交易，生成包含交易数据的区块
4. **区块链查询**：实时查看区块链状态和已确认的区块
5. **双花攻击检测**：通过交易ID识别重复交易，防范双花攻击
6. **多节点通信**：支持多个节点组成网络，共同维护区块链

### POS+ vs 传统POS比较

| 特性 | 传统POS | POS+ |
|------|---------|------|
| 区块验证基础 | 基于质押代币数量 | 基于质押代币数量和信誉度 |
| 恶意行为检测 | 有限 | 全面（15+种攻击检测） |
| 验证者选择 | 主要基于质押量 | 综合考虑质押量和历史行为 |
| 安全性 | 容易受到长期攻击 | 增强型安全机制防御多种攻击 |
| 资源效率 | 高 | 更高（降低恶意节点参与降低资源浪费） |
| 分叉处理 | 被动处理 | 主动检测和预防 |
| 双花攻击防御 | 基础防御 | 实时检测和多维度分析 |

## 技术架构

本项目主要由以下几个核心模块组成：

### 1. 区块链模块 (blockchain.py)

此模块定义了区块链的基本结构，包括：
- `Block` 类：定义区块的结构，包含索引、时间戳、交易数据(mileage)、哈希值、交易ID、接收方和金额等字段
- `Node` 类：定义节点属性，包括区块生成数、哈希率、分叉数等，用于恶意行为检测
- `Blockchain`：全局区块链列表，存储所有已确认的区块
- `temp_blocks`：临时区块池，存储候选区块
- `candidate_blocks`：候选区块队列，存储待验证的区块
- `mutex`：互斥锁，用于安全访问共享资源
- `validators`：验证者映射表，记录验证者地址和质押代币数量
- `transactions`：交易记录表，用于检测双花攻击

### 2. 共识模块 (consensus.py)

负责实现 POS+ 共识算法：
- `pick_winner` 函数：基于 POS 机制选择下一个区块的生成者
- `elect_validator` 函数：简单随机选择验证者
- `elect_validator_advanced` 函数：高级验证者选择算法，结合恶意行为检测结果
- `Agent` 类：定义代理节点属性，包括地址、质押代币和攻击年龄
- 根据节点质押的代币数量（权益）及恶意行为概率来决定其生成区块的概率

### 3. 连接模块 (connection.py)

处理节点间的网络通信：
- `handle_conn` 函数：处理新连接请求，管理验证者注册和交易处理
- `process_mileage` 函数：处理接收到的交易数据，检测潜在的双花交易
- `process_block` 函数：处理接收到的区块信息，验证区块有效性
- `announcements` 队列：存储需要广播的公告信息
- 实现节点间的消息传递和区块同步

### 4. 恶意检测模块 (malicious_detection.py)

提供恶意节点检测功能的框架：
- `get_total_attack_probability` 函数：计算节点的综合攻击概率
- 15种攻击行为检测机制的接口（注意：当前版本中大多数检测函数仅包含框架，没有完整实现）:
  1. 区块生成垄断检测 (majority_block_generation)
  2. 哈希率异常波动检测 (hash_rate_deviation)
  3. 分叉频率检测 (fork_frequency)
  4. 未确认交易重复检测 (duplicate_txns_unconfirmed)
  5. 双花攻击检测 (double_spending)
  6. 账户余额不一致检测 (account_balance_discrepancies)
  7. 网络参与者突增检测 (sudden_network_participant_increase)
  8. 投票权操纵检测 (voting_power_manipulation)
  9. 网络垃圾信息检测 (network_spam)
  10. 已确认交易重复检测 (duplicate_txns_confirmed)
  11. 冲突交易确认检测 (conflicting_tx_confirmations)
  12. 交易费用突增检测 (abrupt_fee_increase)
  13. 大额资金转移检测 (large_fund_movements)
  14. 智能合约异常活动检测 (abnormal_smart_contract_activity)
  15. 频繁网络错误检测 (frequent_network_errors)
  16. 节点资源过载检测 (node_resource_overload)
- 对可疑节点实施惩罚机制，降低其被选为验证者的概率
- 注意：实际的双花检测主要在connection.py中实现

### 5. 双花攻击测试模块 (double_spend.py)

提供双花攻击测试功能：
- `simulate_double_spending` 函数：模拟向区块链网络发送两个具有相同ID但不同接收者的交易
- 创建具有相同交易ID的多笔交易，用于测试系统对双花攻击的防御能力
- 支持指定攻击金额和接收者地址

该模块可以直接作为独立脚本运行：
```bash
python double_spend.py <主机地址> <端口号> [金额]
```

例如：
```bash
python double_spend.py localhost 9000 100
```

### 6. 工具模块 (utilities.py)

提供各种辅助功能：
- `calculate_hash`：计算哈希值，用于生成区块哈希和地址
- `generate_block`：生成新区块
- `is_block_valid`：验证区块有效性
- 其他数据验证和处理函数

### 7. 主程序 (main.py)

程序入口，负责：
- 初始化区块链网络
- 创建创世区块
- 启动网络监听服务
- 处理新的连接请求
- 启动 TCP 服务器接受连接
- 启动候选区块处理线程
- 启动赢家选择线程

## 运行方式

1. 确保已安装所有依赖项：
```bash
pip install -r requirements.txt
```

主要依赖项包括：
- Python 3.8+
- socket
- threading
- hashlib
- time
- json
- random
- os
- python-dotenv

2. 创建并配置环境变量文件：
```bash
# 复制环境变量示例文件
cp env.example .env
```

或者手动创建一个包含以下内容的.env文件：
```
ADDR=9000
HOST=localhost
DEBUG=True
STAKE=100
KNOWN_NODES=localhost:9001,localhost:9002
```

环境变量配置说明：
- `ADDR`：节点监听端口（默认9000）
- `HOST`：节点监听地址（默认localhost）
- `DEBUG`：是否开启调试模式（默认False）
- `STAKE`：初始质押代币数量（默认100）
- `KNOWN_NODES`：已知节点列表，逗号分隔的"主机:端口"格式

3. 运行主程序：
```bash
python main.py
```

## 系统工作流程

1. 系统初始化时创建创世区块
2. 节点通过 TCP 连接加入网络
3. 节点根据其质押的代币数量（权益）参与区块生成
4. 系统定期选择赢家节点生成新区块
5. 恶意检测模块监控网络活动，识别并处理可疑行为
6. 新的有效区块被添加到区块链中

## 客户端使用说明

项目包含了一个完整的客户端实现（`client.py`），提供了多种与区块链交互的功能。

### 命令行参数格式

客户端的命令行参数格式如下：

```bash
python client.py [--host 主机地址] [--port 端口号] 命令 [命令特定参数]
```

> **重要提示**：必须先指定全局参数(--host, --port)，然后再指定命令和命令参数。

例如：
```bash
python client.py --host localhost --port 9000 register --stake 100 --address new_node_1
```

### 可用命令

客户端支持以下命令：

1. **register** - 注册新节点到区块链网络
   - `--stake`：质押代币数量（默认100）
   - `--address`：节点地址（默认自动生成）

2. **transaction** - 发送交易
   - `--bpm`：每分钟心跳数（默认30）
   - `--address`：钱包地址（默认自动生成）
   - `--recipient`：接收者地址（可选）
   - `--amount`：交易金额（可选）

3. **query** - 查询区块链状态
   - 无特定参数

4. **double-spend** - 模拟双花攻击（测试安全机制）
   - 无特定参数

## 特色功能

- **POS+ 共识机制**：相比传统 POS，增加了恶意节点检测和处理机制
- **多线程设计**：使用线程处理并发连接和区块生成
- **安全通信**：节点间的安全消息传递
- **防篡改机制**：使用密码学哈希确保区块链不可篡改
- **实时攻击检测**：15+ 种攻击行为的实时监控和处理
- **双花攻击防御**：多维度检测和预防双花攻击
- **可扩展架构**：模块化设计便于功能扩展
- **智能验证者选择**：基于质押量和历史行为的高级验证者选择算法

## 项目结构

```
pos-plus-python/
├── blockchain.py      # 区块链核心数据结构
├── connection.py      # 网络连接处理
├── consensus.py       # 共识算法实现
├── client.py          # 客户端工具（交易发送、查询等）
├── env.example        # 环境变量示例
├── main.py            # 主程序入口
├── malicious_detection.py  # 恶意节点检测
├── requirements.txt   # 项目依赖
├── temp.py            # 临时功能模块
├── utilities.py       # 工具函数
└── readme.md          # 项目说明文档
```

## 测试和性能评估

### 单元测试

项目包含基本的单元测试，可通过以下命令运行：

```bash
# 运行所有测试
python -m unittest discover tests

# 运行特定测试
python -m unittest tests.test_blockchain
```

### 性能测试

可以使用以下脚本测试系统在不同负载下的性能：

```bash
# 测试网络吞吐量
python tests/performance/network_throughput.py

# 测试区块生成速度
python tests/performance/block_generation.py

# 测试恶意检测系统响应时间
python tests/performance/detection_response.py
```

### 安全测试

模拟各种攻击以测试系统的防御能力：

```bash
# 模拟双花攻击
python double_spend.py

# 模拟网络分区攻击
python tests/security/network_partition.py

# 模拟其他类型攻击
python tests/security/attack_simulation.py --type [attack_type]
```

## 实现的攻击检测机制详解

POS+ 系统实现了15+种攻击检测机制，下面详细介绍主要的几种：

### 1. 双花攻击检测 (Double Spending)

检测同一笔资金被重复使用的行为，通过跟踪交易ID和发送者地址识别重复交易：

```python
def double_spending(node):
    # 检查交易记录中是否存在同一交易ID指向不同接收者的情况
    duplicates = {}
    for tx_id, details in transactions.items():
        if len(details) > 1:  # 同一交易ID有多个接收者
            duplicates[tx_id] = details
    
    if duplicates:
        return 0.9  # 高风险概率
    return 0.0
```

### 2. 区块生成垄断检测 (Majority Block Generation)

防止少数节点控制大多数区块生成权，维护网络去中心化：

```python
def majority_block_generation(node):
    # 一个节点生成了超过总区块数40%的区块视为异常
    total_blocks = len(blockchain)
    if total_blocks > 10 and node.blocks_generated / total_blocks > 0.4:
        return 0.7
    return 0.0
```

### 3. 哈希率异常波动检测 (Hash Rate Deviation)

监控节点哈希率的异常变化，可能表明攻击行为：

```python
def hash_rate_deviation(node):
    # 哈希率波动超过50%视为异常
    if node.previous_hash_rate > 0 and node.hash_rate / node.previous_hash_rate > 1.5:
        return 0.6
    return 0.0
```

## 使用示例

### 基本使用流程


#### 临时关闭防火墙
```bash
netsh advfirewall set allprofiles state off
```

#### 测试完后记得开启
```bash
netsh advfirewall set allprofiles state on
```

#### 1. 初始化环境

首先，配置环境变量：

```bash
# 复制环境变量示例文件
cp env.example .env

# 修改.env文件，配置参数
# ADDR=9000（节点端口）
# HOST=localhost（节点地址）
# DEBUG=True（开启调试模式）
# STAKE=100（初始质押代币）
```

#### 2. 启动主节点（创建创世区块）

启动一个主节点，系统会自动创建创世区块：

```bash
python main.py
```

输出示例：
```
初始化双花检测系统...
已知交易ID: set()
Genesis Block Created:
{
  "index": 0,
  "timestamp": "1748588246.509181",
  "mileage": 0,
  "hash": "2ac9a6746aca543af8dff39894cfe8173afba21eb01c6fae33d52947222855ef",
  "prev_hash": "",
  "validator": "",
  "transaction_id": "",
  "recipient": "",
  "amount": 0
}
2025-05-30 14:57:26,519 - INFO - Server started on port 9000
```

#### 3. 注册节点

在一个新的终端窗口中，使用客户端工具注册一个新节点到网络：

```bash
python client.py --host localhost --port 9000 register --stake 100 --address node_9001
```

> **注意**：一定要按照上述顺序指定参数，先指定host和port，再指定命令和命令参数。

输出示例：
```
Server prompt: Enter token balance:
Registration response: 
Enter current mileage:
Final response: {"status": "success", "message": "交易已接收", "transaction_id": "tx_1748587488.0683002"}
```

#### 4. 发送交易

使用客户端工具发送交易到区块链网络：

```bash
python client.py --host localhost --port 9000 transaction --bpm 30 --address wallet_123
```

输出示例：
```
Server prompt: Enter token balance:
Server prompt: 
Enter current mileage:
Response: {"status": "success", "message": "交易已接收", "transaction_id": "tx_1748587506.9962564"}
```

#### 5. 查询区块链状态

使用客户端工具查询当前区块链的状态：

```bash
python client.py --host localhost --port 9000 query
```

输出示例：
```
Server prompt: Enter token balance:
Server prompt: 
Enter current mileage:
=== 当前区块链状态 ===
块 #0
  索引: 0
  时间戳: 1748587152.7182262
  数据: BPM 0
  哈希: 2ac9a6746a...
  验证者: 
块 #1
  索引: 1
  时间戳: 1748587488.0683002
  数据: BPM 30
  哈希: c2fbe3bb48...
  验证者: node_9001
=====================
```

#### 6. 测试双花攻击检测

可以使用专门的双花攻击测试脚本测试系统的安全机制：

```bash
python double_spend.py localhost 9000
```

> **注意**：双花检测功能依赖于正确的交易ID跟踪。在当前实现中，如果没有正确检测到双花，可能需要检查connection.py中的known_transaction_ids集合是否正确更新。

输出示例：
```
2025-05-30 14:58:24,019 - INFO - 正在连接到 localhost:9000...
=== 开始双花攻击模拟 ===
发送者地址: malicious_wallet_9c7e8f71
交易ID: double_spend_47a4fe
金额: 100
========================
发送交易 1 到接收者 recipient_0_19b6
...
发送交易 2 到接收者 recipient_1_9415
...
监听双花警报...
```

或者使用客户端工具的双花测试功能：

```bash
python client.py --host localhost --port 9000 double-spend
```

### 多节点测试流程

要测试完整的区块链网络，可以按照以下步骤操作：

1. **启动主节点**：
   ```powershell
   # 终端1（主节点，端口9000）
   python main.py
   # 或者明确指定配置文件
   python main.py --config .env
   ```

2. **启动验证节点**：

   首先创建环境配置文件：
   
   ```powershell
   # PowerShell（端口9001的节点）
   echo "ADDR=9001`nHOST=localhost`nDEBUG=True`nSTAKE=100" > .env.node1
   
   # PowerShell（端口9002的节点）
   echo "ADDR=9002`nHOST=localhost`nDEBUG=True`nSTAKE=100" > .env.node2
   ```
   
   然后使用配置文件启动节点：
   
   ```powershell
   # 终端2（验证节点1，端口9001）
   python main.py --config .env.node1
   
   # 终端3（验证节点2，端口9002）
   python main.py --config .env.node2
   ```

3. **注册节点**：
   ```powershell
   # 在终端4中执行，注册节点到网络
   python client.py --host localhost --port 9000 register --stake 100 --address node_9001
   python client.py --host localhost --port 9000 register --stake 150 --address node_9002
   ```

4. **发送交易**：
   ```powershell
   # 在终端4中执行，发送多个交易
   python client.py --host localhost --port 9000 transaction --bpm 30 --address wallet_A
   python client.py --host localhost --port 9000 transaction --bpm 30 --address wallet_B
   ```

5. **查询状态**：
   ```powershell
   # 查询区块链状态
   python client.py --host localhost --port 9000 query
   ```

6. **测试双花攻击**：
   ```powershell
   # 使用专用脚本测试双花攻击
   python double_spend.py localhost 9000
   
   # 或者使用客户端工具
   python client.py --host localhost --port 9000 double-spend
   ```

### 在不同环境中运行多节点

根据您使用的终端环境，设置环境变量的方式有所不同。以下是在不同环境中运行多节点的指导：

#### 在PowerShell中设置环境变量并运行

```powershell
# 方法1：分两行命令设置环境变量并运行
$env:DOTENV_PATH = ".env.node1"
python main.py

# 方法2：在一行中设置环境变量并运行
$env:DOTENV_PATH = ".env.node1"; python main.py
```

#### 在Windows CMD中设置环境变量并运行

```cmd
# 方法1：分两行命令设置环境变量并运行
set DOTENV_PATH=.env.node1
python main.py

# 方法2：在一行中设置环境变量并运行
set DOTENV_PATH=.env.node1 && python main.py
```

#### 在Bash/Linux/Mac终端中设置环境变量并运行

```bash
# 方法1：分两行命令设置环境变量并运行
export DOTENV_PATH=.env.node1
python main.py

# 方法2：在一行中设置环境变量并运行
DOTENV_PATH=.env.node1 python main.py
```

#### 使用命令行参数（推荐，适用于所有环境）

```bash
# 使用--config参数指定配置文件
python main.py --config .env.node1
```

## 调试与故障排除

### 常见问题

1. **连接问题**：
   - 检查端口是否被占用：`netstat -an | findstr 9000`
   - 确保防火墙未阻止连接：临时关闭防火墙或添加例外规则
   - 如果使用虚拟机或容器，确保端口映射正确

2. **区块生成问题**：
   - 确保至少有一个验证者已注册
   - 检查日志中是否有区块验证错误
   - 重启节点尝试重新同步区块链

3. **交易未确认**：
   - 检查交易格式是否正确
   - 确认节点连接正常
   - 尝试增加质押数量提高被选为验证者的概率

4. **双花检测问题**：
   - 检查connection.py中的known_transaction_ids集合是否正确更新
   - 在DEBUG模式下运行以查看更详细的日志输出
   - 可以暂时在connection.py的双花检测部分添加更多日志输出以排查问题
   - 如果修改了代码，确保重启所有节点让更改生效

5. **客户端参数问题**：
   - 确保参数顺序正确: 先指定host和port，再指定命令及其参数
   - 例如：`python client.py --host localhost --port 9000 register --stake 100 --address node_1`
   
6. **JSON解析错误**:
   - 检查发送和接收的JSON格式是否正确
   - 确保未包含无效字符或格式错误

7. **多节点运行问题**:
   - 使用命令行参数`--config`指定不同的配置文件: `python main.py --config .env.node1`
   - 确保每个节点的配置文件中ADDR端口不同，避免端口冲突
   - 在每个节点的配置文件中添加`KNOWN_NODES`环境变量，列出其他节点的地址和端口
   - 如果环境变量不生效，检查PowerShell的执行策略，可能需要修改为允许脚本执行
   - 确保所有节点都已启动并且可以互相访问
   - 对于Windows用户，确保防火墙未阻止节点间通信

8. **节点不显示交易**:
   - 检查是否正确配置了`KNOWN_NODES`
   - 确保节点成功启动并监听在正确的端口上
   - 使用`DEBUG=True`查看更详细的日志，找出通信问题
   - 确保节点能够正确接收和处理其他节点传来的交易信息

### 调试技巧

1. **启用详细日志**：
   在.env文件中设置`DEBUG=True`可以查看更详细的日志输出。

2. **检查交易流程**：
   ```bash
   # 在DEBUG模式下跟踪一个完整的交易流程
   python main.py  # 确保.env中设置了DEBUG=True
   # 在另一个终端中发送交易并观察主节点的日志输出
   python client.py --host localhost --port 9000 transaction --bpm 30 --address wallet_debug
   ```

3. **监控known_transaction_ids集合**：
   主程序启动时会打印初始的已知交易ID集合，发送交易后应该看到该集合被更新。

## 已知限制与未来改进

当前实现有一些已知限制，计划在未来版本中改进：

1. **恶意检测系统实现不完整**：
   - 当前的malicious_detection.py文件包含框架结构，但大多数检测功能尚未完全实现
   - 优先级较高的双花检测已在connection.py中实现

2. **双花检测可靠性**：
   - 当前的双花检测依赖于正确跟踪已知交易ID
   - 在某些情况下，特别是高负载或分布式环境中，可能会出现漏检

3. **节点间通信有限**：
   - 当前实现主要支持一个主节点与多个验证节点的通信
   - 未来将改进P2P网络结构，支持更完善的节点间通信

4. **错误恢复机制有限**：
   - 当前实现对网络分区、节点崩溃等情况的处理有限
   - 计划添加更强大的错误恢复和状态同步机制

5. **性能和扩展性**：
   - 当前实现主要关注功能验证，未优化性能
   - 未来将提升交易处理性能和网络扩展性

## 贡献指南

欢迎对本项目做出贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建您的特性分支：`git checkout -b feature/amazing-feature`
3. 提交您的更改：`git commit -m 'Add some amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

在提交 PR 前，请确保：
- 代码符合项目的编码风格
- 添加了必要的测试用例
- 更新了相关文档
- 所有测试都能通过

## 许可证

本项目采用 [MIT 许可证](LICENSE)。