# MRL-PoS Blockchain

A custom MRl-POS blockchain implemented with Go.

## Installation

First, download and install Go from [here](https://go.dev/dl/). Open this project in any code editor and install the third party dependencies.

```bash
go get github.com/joho/godotenv
go get github.com/davecgh/go-spew/spew
```

## Configuring environment variables

Clone the `.env.example` file and rename it to `.env`. You can also change the address port you want to run. By default it will start using port 9000.

## Running the project

First start the TCP server

```bash
go run .
```

Then for connecting a new node/validator, open a new terminal and run the following command

```bash
nc localhost 9000
```

## MRL-POS项目代码文件结构

### 主要Go代码文件
- **main.go**: 程序入口点，配置并启动区块链
- **blockchain.go**: 定义区块链结构，包括Block和Node类型
- **connection.go**: 处理节点间的网络连接
- **consensus.go**: 实现共识算法和验证者选举
- **maliciousDetection.go**: 恶意行为检测算法实现
- **utilities.go**: 实用函数，包括哈希计算和区块生成
- **temp.go**: 临时文件，包含DDoS攻击检测函数

### 配置和说明文件
- **.env.example**: 环境变量示例配置
- **go.mod**: Go模块定义
- **LICENSE**: GNU通用公共许可证
- **readme.md**: 项目说明文档

### 上层目录
- **README.md**: 项目总体说明（位于上一级目录）

## License

[GNU](https://www.gnu.org/licenses/)
