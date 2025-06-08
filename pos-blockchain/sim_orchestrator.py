# Copyright (c) 2025 An Hongxu
# Peking University - School of Software and Microelectronics
# Email: anhongxu@stu.pku.edu.cn
#
# For academic use only. Commercial usage is prohibited without authorization.

"""
PoS 区块链模拟 统一调度器
一个用于 PoS 区块链模拟的统一调度器，支持配置化的时间轴事件调度。
配置示例见末尾。
用法示例示例：
```bash
python sim_orchestrator.py fork_demo.yml --debug  # 交互式逐秒
```
按 Enter → 下一秒；随时输入 q + Enter 退出。
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import yaml 

# =============================================================================
# 时间解析
# =============================================================================

def parse_duration(value: str | int | float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    txt = str(value).strip().lower()
    total, num = 0.0, ""
    units = {"ms": 0.001, "s": 1, "m": 60, "h": 3600}
    i = 0
    while i < len(txt):
        if txt[i].isdigit() or txt[i] == ".":
            num += txt[i]
            i += 1
            continue
        for u in ("ms", "s", "m", "h"):
            if txt.startswith(u, i):
                if not num:
                    raise ValueError(f"时间串 '{txt}' 在 '{u}' 前缺数字")
                total += float(num) * units[u]
                num = ""
                i += len(u)
                break
        else:
            raise ValueError(f"非法时间串 '{txt}' at {i}")
    if num:
        total += float(num)
    return total

# =============================================================================
# 数据结构
# =============================================================================

@dataclass
class TimedCommand:
    time: float
    target: str  # "server" 或 节点 ID
    command: str
    order: int

@dataclass
class ProcessHandle:
    name: str
    cmd: List[str]
    proc: Optional[asyncio.subprocess.Process] = field(default=None, init=False)
    log: logging.Logger = field(init=False)

    async def start(self):
        self.proc = await asyncio.create_subprocess_exec(
            *self.cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        self._setup_logging()
        logging.info("启动 %s (pid=%s)", self.name, self.proc.pid)
        asyncio.create_task(self._pump_output())

    def _setup_logging(self):
        root_debug = logging.getLogger().isEnabledFor(logging.DEBUG)
        self.log = logging.getLogger(f"proc.{self.name}")
        self.log.propagate = False
        if root_debug:
            self.log.setLevel(logging.DEBUG)
            fh = logging.FileHandler(f"{self.name}.debug.log")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            self.log.addHandler(fh)
        else:
            self.log.disabled = True

    async def _pump_output(self):
        assert self.proc and self.proc.stdout
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                break
            msg = line.decode(errors="ignore").rstrip()
            self.log.debug(msg)
            logging.debug("[%s] %s", self.name, msg)

    async def send(self, line: str):
        if not self.proc or not self.proc.stdin:
            raise RuntimeError(f"{self.name} stdin 不可用")
        logging.info(">>> (%s) %s", self.name, line)
        self.proc.stdin.write((line + "\n").encode())
        await self.proc.stdin.drain()

    async def graceful_stop(self, timeout: float = 5.0) -> bool:
        try:
            await self.send("exit")
        except RuntimeError:
            pass
        try:
            await asyncio.wait_for(self.proc.wait(), timeout)
            logging.info("%s 已优雅退出", self.name)
            return True
        except asyncio.TimeoutError:
            logging.warning("%s 未在 %.1fs 内退出", self.name, timeout)
            return False

    async def force_stop(self):
        if not self.proc:
            return
        logging.warning("强制终止 %s", self.name)
        self.proc.terminate()
        try:
            await asyncio.wait_for(self.proc.wait(), 3)
        except asyncio.TimeoutError:
            logging.error("%s kill -9", self.name)
            self.proc.kill()

# =============================================================================
# 主控制器
# =============================================================================

class SimulationOrchestrator:
    def __init__(self, cfg_path: str | Path, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.cfg = self._load_cfg(cfg_path)

        # ---- 全局 ----
        self.python_bin = self.cfg.get("python_bin", "python")
        self.server_host = self.cfg.get("server_host", "127.0.0.1")
        self.server_port = int(self.cfg.get("server_port", 5000))
        self.server_ready_timeout = float(self.cfg.get("server_ready_timeout", 10))
        self.node_exit_wait = float(self.cfg.get("node_exit_wait", 5))
        self.post_wait = float(self.cfg.get("post_wait", 3))

        # ---- 日志 ----
        logging.basicConfig(
            level=getattr(logging, self.cfg.get("log_level", "INFO").upper()),
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler(), *( [logging.FileHandler(self.cfg["log_file"])] if self.cfg.get("log_file") else [] )],
        )

        # ---- 进程 ----
        self.server = ProcessHandle("server", self._parse_cmd(self.cfg["server"]["cmd"]))
        self.nodes: Dict[str, ProcessHandle] = {
            nid: ProcessHandle(nid, self._parse_cmd(cfg["cmd"]))
            for nid, cfg in self.cfg.get("nodes", {}).items()
        }

        # ---- 时间轴 ----
        self.timeline = self._build_timeline()

    # ------------------------------------------------------------------
    # 配置解析
    # ------------------------------------------------------------------

    @staticmethod
    def _load_cfg(path: str | Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _sub_py(self, cmd: str) -> str:
        if "{python}" in cmd:
            return cmd.replace("{python}", self.python_bin, 1)
        if cmd.startswith("python ") or cmd.startswith("python3 "):
            parts = cmd.split(maxsplit=1)
            return f"{self.python_bin} {parts[1]}" if len(parts) == 2 else self.python_bin
        return cmd

    def _parse_cmd(self, cmd: str | Sequence[str]) -> List[str]:
        import shlex
        return list(cmd) if isinstance(cmd, (list, tuple)) else shlex.split(self._sub_py(cmd))

    def _build_timeline(self):
        tl: List[TimedCommand] = []
        order = 0
        for e in self.cfg.get("timeline", []):
            t = parse_duration(e["at"])
            cmds = e["run"] if isinstance(e["run"], list) else [e["run"]]
            for c in cmds:
                tl.append(TimedCommand(t, e["target"], c, order))
                order += 1
        tl.sort(key=lambda x: (x.time, x.order))
        return tl

    # ------------------------------------------------------------------
    # 服务器Probe
    # ------------------------------------------------------------------

    async def _wait_server_ready(self) -> bool:
        deadline = asyncio.get_event_loop().time() + self.server_ready_timeout
        logging.info("等待服务器 %s:%s …", self.server_host, self.server_port)
        while asyncio.get_event_loop().time() < deadline:
            try:
                reader, writer = await asyncio.open_connection(self.server_host, self.server_port)
                writer.close(); await writer.wait_closed()
                logging.info("服务器端口就绪")
                return True
            except (ConnectionRefusedError, OSError):
                await asyncio.sleep(0.3)
        logging.error("服务器就绪超时")
        return False

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------

    async def run(self):
        await self.server.start()
        if not await self._wait_server_ready():
            await self.server.force_stop(); return
        for ph in self.nodes.values():
            await ph.start()
        if self.debug_mode:
            await self._run_debug_interactive()
        else:
            await self._run_normal()
        await self._shutdown()

    async def _run_normal(self):
        async def schedule(item: TimedCommand):
            await asyncio.sleep(item.time)
            h = self.server if item.target == "server" else self.nodes[item.target]
            await h.send(item.command)
        await asyncio.gather(*[asyncio.create_task(schedule(i)) for i in self.timeline])

    async def _run_debug_interactive(self):
        logging.info("DEBUG 模式：按 Enter 推进 1 秒，输入 q 退出")
        max_t = max((c.time for c in self.timeline), default=0)
        current, idx = 0, 0
        loop = asyncio.get_event_loop()
        while current <= max_t:
            # 执行本秒命令
            window_end = current + 1
            executed = False
            while idx < len(self.timeline) and self.timeline[idx].time < window_end:
                c = self.timeline[idx]
                h = self.server if c.target == "server" else self.nodes[c.target]
                await h.send(c.command)
                executed = True; idx += 1
            if not executed:
                logging.debug("[DEBUG] %ds 无命令", current)
            # 用户输入控制
            try:
                user_in = await loop.run_in_executor(None, input, f"[{current}s] Enter=Next | q=Quit > ")
            except (EOFError, KeyboardInterrupt):
                user_in = "q"
            if user_in.strip().lower() in ("q", "quit", "exit"):
                logging.info("调试提前结束")
                break
            current += 1

    async def _shutdown(self):
        if self.post_wait > 0:
            logging.info("结束等待 %.1fs…", self.post_wait)
            try:
                await asyncio.sleep(self.post_wait)
            except asyncio.CancelledError:
                pass
        if not await self.server.graceful_stop():
            await self.server.force_stop()
        if self.nodes:
            logging.info("等待节点自动下线 %.1fs…", self.node_exit_wait)
            try:
                await asyncio.sleep(self.node_exit_wait)
            except asyncio.CancelledError:
                pass
        for ph in self.nodes.values():
            if ph.proc and ph.proc.returncode is None:
                await ph.force_stop()

# =============================================================================
# CLI 入口
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="PoS 区块链实验编排器")
    parser.add_argument("config", help="YAML 配置文件路径")
    parser.add_argument("--debug", action="store_true", help="逐秒执行调试模式")
    args = parser.parse_args()

    orch = SimulationOrchestrator(args.config, debug_mode=args.debug)
    loop = asyncio.get_event_loop()

    def _on_sig():
        logging.warning("捕获终止信号，正在优雅收尾…")
        for t in asyncio.all_tasks(loop):
            t.cancel()

    loop.add_signal_handler(signal.SIGINT, _on_sig)
    loop.add_signal_handler(signal.SIGTERM, _on_sig)

    try:
        loop.run_until_complete(orch.run())
    finally:
        loop.close()

# =============================================================================
# YAML 配置示例
# =============================================================================

"""
# sample_config.yml
python_bin: python3        # 可选； python / python3 / 指定绝对路径
working_dir: .
log_level: INFO
log_file: orchestration.log

server:
  cmd: "{python} aserver.py"   # 用占位符自动替换

nodes:
  node1: { cmd: "{python} node.py --node node1" }
  node2: { cmd: "{python} node.py --node node2" }

post_wait: 4         # 时间轴跑完后再等 4 秒才退出
node_exit_wait: 6    # server exit 后给节点 6 秒清理

timeline:
  - at: 0
    target: server
    run: "stop"

  - at: 5s
    target: node1
    run: "stake 100"

  - at: 10s
    target: server
    run: "step"
"""

# =============================================================================
if __name__ == "__main__":
    main()

