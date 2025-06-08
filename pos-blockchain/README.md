# 基于 PoS 的区块链模拟框架

**Proof-of-Stake 区块链模拟器，支持分叉与投票机制**  
作者：安鸿旭（北京大学软件与微电子学院）  
邮箱：anhongxu@stu.pku.edu.cn  

> **仅限学术用途，禁止未经授权的商业使用。**

---

## 项目特点

| 功能             | 说明                                                         |
| ---------------- | ------------------------------------------------------------ |
| **C/S 架构**     | 节点通过中心服务器转发消息，可模拟延迟、丢包                 |
| **PoS 共识**     | 质押决定出块权，可选投票确认机制                             |
| **链分叉与重组** | 支持 Nothing-at-Stake 等场景，带交易池回收                   |
| **自动同步**     | 新节点上线自动拉取主链                                       |
| **交易类型**     | 转账 / 质押 / 解质押                                         |
| **实验编排工具** | **sim_orchestrator.py**：YAML 一键批量启动、多节点故障注入、交互式调试 |

---

## 系统架构

```
+------------+       +------------+       +------------+
 |   Node 1   | <---> |   Server   | <---> |   Node N   |
 +------------+       +------------+       +------------+
```

* **Server** — 节点消息中转，可模拟网络故障  
* **Node** — 维护本地区块链 & 钱包，负责出块 / 同步 / 投票  
* **Blockchain / WalletManager / Client** — 见源码注释  
* **消息协议** — protobuf：`HELLO / BLOCK / VOTE / STEP …`

---

## 快速开始

### 依赖安装

```bash
pip install -r requirements.txt        # protobuf等
```

### 配置文件 (`config.yaml`) 示例

```yaml
server:
  host: "127.0.0.1"
  port: 5000


sync:
  timeout: 2.0

step:
  interval: 5.0

vote:
  enabled: false 
  timeout: 5.0
  threshold: 0.66


initial_state:
  node1:
    balance: 100.0
    stake: 0.0
  node2:
    balance: 100.0
    stake: 0.0
  node3:
    balance: 100.0
    stake: 0.0
```

### 启动

```bash
# 1) 服务器（可加 --debug, 手动step）
python aserver.py

# 2) 节点
python node.py --node node1
python node.py --node node2
```

------

## Node & Server 常用命令

| Node                                     | Server                                 |
| ---------------------------------------- | -------------------------------------- |
| `sync` — 主动同步                        | `step` — 手动广播 STEP                 |
| `nodes` — 列表节点                       | `stop / continue` — 关闭/恢复自动 STEP |
| `tx <to> <amt>` — 转账                   | `drop <id> on/off/toggle` — 丢包       |
| `stake / unstake <amt>                   | `delay <node_id> <ms|off>` — 网络延迟  |
| `forge [--force]` — 出块                 | `exit` — 关闭服务器                    |
| `chain / wallet / mempool / info / exit` |                                        |

------

## 投票确认机制

- **关闭**（默认）：收到区块即入链
- **开启**：区块需在 `vote.timeout` 秒内收集到 `threshold × 验证者数` 的票方可加入主链

------

## Orchestrator：批量编排

### 功能概览

| 亮点            | 描述                                                         |
| --------------- | ------------------------------------------------------------ |
| **YAML 时间轴** | `at` 支持 `3s / 1m30s`，`run` 支持字符串或列表               |
| **端口探测**    | server 端口就绪后才启动节点，避免连接被拒                    |
| **交互调试**    | `--debug`：按 **Enter** 推进 1 秒，`q` 退出                  |
| **独立日志**    | `log_level: DEBUG` 时生成 `server.debug.log`, `node1.debug.log`… |
| **优雅退出**    | 时间轴→`post_wait`→server `exit`→等待节点→强制收尾           |

### YAML 示例：制造分叉

```yaml
python_bin: python3          
working_dir: .
log_level: DEBUG             # INFO-不显示节点输出 DEBUG-显示节点输出,便于调试
log_file: fork_demo.log

server:
  cmd: "{python} aserver.py"

nodes:
  node1: { cmd: "{python} node.py --node node1" }
  node2: { cmd: "{python} node.py --node node2" }

# 收尾参数
post_wait: 5         # 时间轴结束后再等 5 秒
node_exit_wait: 5    # server exit 后给节点 5 秒自毁

timeline:
  - at: 0
    target: server
    run: "stop"                # 关闭自动 STEP，改为手动控制节奏

  - at: 2s
    target: server
    run: "drop node2 on"       # 手动隔离 node2，模拟网络分区, node2无法接收到消息 但是可以发送消息

  - at: 5s
    target: node1
    run: ["stake 10", "tx node2 10"]

  - at: 5s
    target: node2
    run: "stake 10"          

  - at: 7s
    target: node1 
    run: "forge --force"       # node1 强制出块（高度 H）

  - at: 8s
    target: node2
    run: "forge --force"       # node2 强制出块（高度 H）此时node1收到该block 高度相同 暂存不切换

  - at: 10s
    target: node2
    run: ["tx node1 10", "forge --force"]  # node2 发送交易给 node1 并出块（高度 H+1）, 此时node1收到这个block 高度 H+1 切换到 node2 的链上, 并恢复node1链上的交易

  - at: 12s
    target: node1
    run: "info"

  - at: 12s
    target: node2
    run: "info"
```

启动：

```bash
python sim_orchestrator.py fork_demo.yml          # 普通模式
python sim_orchestrator.py fork_demo.yml --debug  # 交互调试
```

------

## 配置字段速查

| 区块 / 字段                   | 作用                       |
| ----------------------------- | -------------------------- |
| `server.host / port`          | 服务器监听地址与端口       |
| `sync.timeout`                | 节点同步等待秒数           |
| `step.interval`               | 自动 STEP 周期             |
| `vote.*`                      | 投票机制开关 / 超时 / 阈值 |
| `initial_state`               | 各节点初始余额 & 质押      |
| Orchestrator `python_bin`     | 替换 YAML 中 `{python}`    |
| Orchestrator `post_wait`      | 时间轴结束后延迟退出       |
| Orchestrator `node_exit_wait` | 服务器 exit 后等待节点秒数 |

------

## 免责声明

- 本项目仅用于学术研究与教学演示
- 禁止任何未经许可的商业用途或生产部署
- 共识 / 网络逻辑已做简化，**非** 完整生产级区块链实现
