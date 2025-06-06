# POS+ 区块链项目

一个基于权益证明（Proof of Stake）共识机制的分布式区块链实现，具有恶意行为检测和双花攻击防护功能。

## 项目结构

```
pos-plus-python/
├── README.md                   # 项目说明文档
├── requirements.txt            # Python依赖包
├── .env                       # 环境配置文件
├── env.example               # 配置文件示例
├── main.py                   # 主程序入口
├── blockchain.py             # 区块链核心数据结构
├── utilities.py              # 工具函数集合
├── consensus.py              # 共识算法实现
├── connection.py             # 网络连接与节点通信
├── malicious_detection.py    # 恶意行为检测模块
├── client.py                 # 统一客户端接口
├── start_network.py          # 多节点启动助手
├── test_blockchain.py        # 区块链功能测试
└── test_network_sync.py      # 网络同步测试
```


## 核心功能

### 1. 区块链核心 (`blockchain.py`)
- **Block类**: 区块数据结构，包含索引、时间戳、交易数据、哈希值等
- **Node类**: 节点信息管理，包括算力、声誉、分叉统计等
- **全局变量**: 区块链、候选区块、验证者等核心数据结构

### 2. 共识机制 (`consensus.py`)
- **权益证明算法**: 基于质押代币数量选择验证者
- **彩票池机制**: 质押越多，被选中概率越高
- **高级选举算法**: 考虑恶意行为历史的验证者选择

### 3. 网络通信 (`connection.py`)
- **节点连接管理**: 处理入站和出站连接
- **消息协议**: JSON格式的消息传递
- **区块链同步**: 自动与网络中其他节点同步
- **双花检测**: 实时检测和阻止双花攻击

### 4. 安全机制 (`malicious_detection.py`)
- **多维度检测**: 算力偏差、分叉频率、投票权操控等
- **风险评估**: 计算节点的恶意行为概率
- **实时监控**: 持续监控网络中的异常行为

## 主要特性

### 🔒 安全性
- **双花攻击防护**: 检测并阻止重复交易ID
- **恶意节点识别**: 多指标综合评估节点可信度
- **网络同步验证**: 确保区块链一致性

### 🌐 分布式
- **P2P网络**: 去中心化的节点间通信
- **自动发现**: 动态发现和连接网络节点
- **故障恢复**: 节点掉线后自动重连

### ⚡ 性能
- **权益证明**: 相比工作量证明更节能
- **并发处理**: 多线程处理网络连接和共识
- **快速同步**: 智能区块链同步机制

## 安装与使用

### 环境要求
- Python 3.8+
- 依赖包：`python-dotenv`

### 1. 安装依赖


### 2. 配置节点
复制配置文件并根据需要修改：
```bash
cp env.example .env
```

编辑 `.env` 文件：
```env
# 节点网络配置
SERVER_HOST=localhost
SERVER_PORT=9000
ADDR=9000

# 已知节点列表
KNOWN_NODES=localhost:9001,localhost:9002

# 调试配置
DEBUG=True
STAKE=100
```

### 3. 启动节点
```bash
python main.py
```

使用自定义配置文件：
```bash
python main.py --config custom.env
```

## 使用示例

### 1. 启动多节点网络

**节点1 (端口9000)**:
```bash
# 修改 .env 文件
SERVER_PORT=9000
KNOWN_NODES=localhost:9001,localhost:9002

python main.py
```

**节点2 (端口9001)**:
```bash
# 修改 .env 文件
SERVER_PORT=9001
KNOWN_NODES=localhost:9000,localhost:9002

python main.py
```

**节点3 (端口9002)**:
```bash
# 修改 .env 文件
SERVER_PORT=9002
KNOWN_NODES=localhost:9000,localhost:9001

python main.py
```

### 2. 使用统一客户端进行操作

所有网络操作都可以通过统一的客户端工具完成：

**注册验证者节点**:
```bash
python client.py register --stake 100 --address node_1
```

**发送交易**:
```bash
python client.py --port 9002 transaction --bpm 30 --address node_2
```

**查询区块链状态**:
```bash
python client.py query
```

**测试双花攻击**:
```bash
python client.py double-spend
```

## 网络消息协议

### 注册消息
```json
{
    "type": "REGISTER",
    "address": "node_address",
    "stake": 100,
    "node_addr": "localhost",
    "node_port": 9000
}
```

### 交易消息
```json
{
    "type": "TRANSACTION",
    "BPM": 30,
    "address": "sender_address",
    "recipient": "recipient_address",
    "amount": 100,
    "id": "unique_transaction_id"
}
```

### 查询消息
```json
{
    "type": "QUERY",
    "query": "BLOCKCHAIN_STATUS"
}
```

### 心跳消息
```json
{
    "type": "HEARTBEAT",
    "from": "node_address"
}
```

## 安全机制详解

### 双花攻击防护
1. **交易ID唯一性检查**: 维护全局已知交易ID集合
2. **实时检测**: 接收交易时立即检查重复性
3. **网络广播**: 检测到攻击时向所有节点发送警报
4. **自动拒绝**: 拒绝处理重复交易ID的交易

### 恶意节点检测
1. **算力偏差监控**: 检测异常的算力变化
2. **分叉频率统计**: 监控节点创建分叉的频率
3. **投票权集中度**: 检测是否有节点控制过多质押
4. **综合评分**: 基于多个指标计算恶意概率

## 测试

### 运行功能测试
```bash
# 测试区块链基本功能和网络连接
python test_blockchain.py

# 测试网络同步性能
python test_network_sync.py
```

### 安全功能测试
使用统一客户端测试安全功能：
```bash
# 测试双花攻击检测
python client.py double-spend
```

## 开发指南

### 添加新的消息类型
1. 在 `connection.py` 的 `process_mileage()` 函数中添加新的消息处理逻辑
2. 定义JSON消息格式
3. 实现相应的处理函数

### 扩展恶意检测
1. 在 `malicious_detection.py` 中添加新的检测函数
2. 更新 `get_total_attack_probability()` 函数的权重配置
3. 添加相应的数据收集逻辑

### 优化共识算法
1. 修改 `consensus.py` 中的 `pick_winner()` 函数
2. 实现新的验证者选择策略
3. 调整选举权重和概率分布

## 故障排除

### 常见问题

**1. 节点无法连接**
- 检查防火墙设置
- 确认端口未被占用
- 验证 `KNOWN_NODES` 配置

**2. 区块链同步失败**
- 检查网络连接
- 确认其他节点正常运行
- 查看日志文件中的错误信息

**3. 交易被拒绝**
- 检查交易ID是否唯一
- 确认发送者地址有效
- 验证交易格式是否正确

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 贡献

欢迎提交问题报告和功能请求！如需贡献代码，请：

1. Fork 本仓库
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 GitHub Issue
- 发送邮件至项目维护者

---

**注意**: 这是一个教育和研究项目，不建议在生产环境中使用。
