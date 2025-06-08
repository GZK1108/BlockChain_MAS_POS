# Copyright (c) 2025 An Hongxu
# Peking University - School of Software and Microelectronics
# Email: anhongxu@stu.pku.edu.cn
#
# For academic use only. Commercial usage is prohibited without authorization.

import asyncio
import sys
import struct
import message_pb2
import contextlib

from utils import load_config
from logger import setup_logger
from decorators import message_handler, command

logger = setup_logger("server")

class BlockchainServerAsync:
    def __init__(self, host, port, debug_mode=False):
        self.host = host
        self.port = port

        self.clients = {}  # writer -> node_id

        self.message_handlers = {}
        self.commands = {}
        self._register_message_handlers()
        self._register_commands()

        self.debug_mode = debug_mode
        step_config = load_config(section="step")
        self.step_interval = step_config.get("interval", 5.0)  # Default to 5 second if not set 
        self._step_task = None
        self._stdin_task = None

        self.drop_set: set[str] = set()        # 丢包节点
        self.delay_map: dict[str, float] = {}  # node_id -> delay sec

    async def start(self):
        """Start the asynchronous server."""
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        logger.info(f"Async server started on {self.host}:{self.port}")
        
        if not self.debug_mode:
            self._step_task = asyncio.create_task(self._step_loop())

        loop = asyncio.get_running_loop()
        self._stdin_task = loop.create_task(self._stdin_loop())


        try:
            async with self.server:
                await self.server.serve_forever()  
        except asyncio.CancelledError:         
            pass

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a new client connection."""
        addr = writer.get_extra_info('peername')
        logger.info(f"New connection from {addr}")
        self.clients[writer] = None

        buffer = b""
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                buffer += data
                while True:
                    if len(buffer) < 4:
                        break
                    msg_len = struct.unpack('>I', buffer[:4])[0]
                    if len(buffer) < 4 + msg_len:
                        break
                    raw_msg = buffer[4:4+msg_len]
                    buffer = buffer[4+msg_len:]

                    msg = message_pb2.Message()
                    msg.ParseFromString(raw_msg)

                    logger.info(
                        f"received message [{message_pb2.Message.MessageType.Name(msg.type)}]\n"
                        f"  sender   : {msg.sender_id}\n"
                        f"  full msg : \n{msg}"
                    )
                    await self._handle_message(writer, msg)
        except Exception as e:
            logger.error(f"Error in client {addr}: {e}")
        finally:
            await self._disconnect_client(writer)

    async def _broadcast_step(self):
        """Broadcast a STEP message to all connected nodes."""
        msg = message_pb2.Message()
        msg.type = message_pb2.Message.STEP
        msg.sender_id = "server"
        await self._broadcast(msg)
        logger.info("[STEP] Broadcasted STEP message to all nodes.")

    async def _step_loop(self):
        """Periodically broadcast STEP messages."""
        while True:
            await asyncio.sleep(self.step_interval)
            await self._broadcast_step()

    async def _send_immediate(self, writer, packet):
        """Send a packet immediately to the client."""
        try:
            writer.write(packet)
            await writer.drain()
        except ConnectionError:
            await self._disconnect_client(writer)
        except Exception as e:
            logger.error(f"Failed to send to {self.clients.get(writer) or 'unknown'}: {e}")

    async def _send_with_delay(self, writer, packet, delay):
        """Send a packet to the client with a delay."""
        try:
            await asyncio.sleep(delay)
            writer.write(packet)
            await writer.drain()
        except ConnectionError:
            await self._disconnect_client(writer)
        except Exception as e:
            logger.error(f"Failed to send to {self.clients.get(writer) or 'unknown'}: {e}")

    async def _broadcast(self, message, exclude=None):
        """Broadcast a message to all connected clients."""
        data = message.SerializeToString()
        prefix = struct.pack('>I', len(data))
        packet = prefix + data
        for writer, node_id in list(self.clients.items()):
            if writer is exclude:
                continue

            # 模拟丢包: 直接跳过
            if node_id in self.drop_set:
                continue

            # 模拟延迟: 走异步延迟发送
            delay = self.delay_map.get(node_id)
            if delay:
                asyncio.create_task(self._send_with_delay(writer, packet, delay))
            else:
                await self._send_immediate(writer, packet)

    async def _disconnect_client(self, writer):
        """Disconnect a client and notify others."""
        node_id = self.clients.pop(writer, None)
        if node_id is None:
            return

        logger.info(f"Node {node_id} disconnected.")
        msg = message_pb2.Message()
        msg.type = message_pb2.Message.BYE
        msg.sender_id = node_id
        await self._broadcast(msg)

        if writer in self.clients:
            del self.clients[writer]
        writer.close()
        await writer.wait_closed()

    async def _notify_shutdown(self):
        """Notify all clients about server shutdown."""
        msg = message_pb2.Message()
        msg.type = message_pb2.Message.BYE
        msg.sender_id = "server"
        await self._broadcast(msg)

    async def _handle_message(self, writer, message):
        """Handle incoming messages based on their type."""
        handler = self.message_handlers.get(message.type)
        if handler:
            await handler(writer, message)
        else:
            await self._default_message_handler(writer, message)

    async def _default_message_handler(self, writer, message):
        """Default message handler for unrecognized message types."""
        await self._broadcast(message, exclude=writer)

    def _register_commands(self):
        """Register commands from methods decorated with @command."""
        for attr in dir(self):
            method = getattr(self, attr)
            if callable(method) and hasattr(method, "_is_command"):
                name = method._command_name
                help_text = method._help_text
                self.commands[name] = {"func": method, "help": help_text}

    def _register_message_handlers(self):
        """Register message handlers from methods decorated with @message_handler."""
        for attr in dir(self):
            method = getattr(self, attr)
            if callable(method) and hasattr(method, "_is_message_handler"):
                msg_type = method._msg_type
                self.message_handlers[msg_type] = method
                logger.debug(f"Registered message handler for type {msg_type}: {method.__name__}")

    async def _stdin_loop(self):
        """Read commands from stdin in a non-blocking way."""
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                cmd = line.decode().strip()
                if cmd:
                    await self._handle_command(cmd)
        except asyncio.CancelledError:
            return 

    async def _handle_command(self, cmd):
        """Handle commands entered in the console."""
        parts = cmd.strip().split()
        if not parts:
            return
        name = parts[0]
        args = parts[1:]
        command = self.commands.get(name)
        if command:
            try:
                await command["func"](args)
            except Exception as e:
                logger.error(f"Error executing '{name}': {e}")
        else:
            logger.warning(f"Unknown command: {name}. Type 'help' for available commands.")

    @message_handler(message_pb2.Message.HELLO)
    async def handle_hello(self, writer, message):
        """Handle HELLO messages from clients."""
        self.clients[writer] = message.sender_id
        await self._default_message_handler(writer, message)

    @command("step", "Manually broadcast a STEP message")
    async def _cmd_step(self, args):
        await self._broadcast_step()

    @command("stop", "Stop sending STEP messages")
    async def _cmd_stop(self, args):
        if self._step_task:
            self._step_task.cancel()
            self._step_task = None
            logger.info("Stopped sending STEP messages")

    @command("continue", "Continue sending STEP messages")
    async def _cmd_continue(self, args):
        if not self._step_task:
            self._step_task = asyncio.create_task(self._step_loop())
            logger.info("Continuing sending STEP messages")

    @command("help", "Show available server commands")
    async def _cmd_help(self, args):
        print("Available server commands:")
        for name, info in self.commands.items():
            print(f"  {name.ljust(10)} - {info['help']}")

    async def _graceful_shutdown(self):
        """Gracefully shut down the server."""
        logger.info("Shutting down server...")

        if self._step_task:
            self._step_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._step_task
            self._step_task = None

        # current = asyncio.current_task()
        if self._stdin_task: # and self._stdin_task is not current:
            self._stdin_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stdin_task
            self._stdin_task = None

        self.drop_set.clear()
        self.delay_map.clear()
        await self._notify_shutdown()

        logger.info("Closing all client connections...")
        for writer in list(self.clients.keys()):
            await self._disconnect_client(writer)

        self.clients.clear()

        if self.server:
            logger.info("Closing server socket...")
            self.server.close()
            await self.server.wait_closed()
            self.server = None

        logger.info("Server shutdown complete. Bye!")

    @command("exit", "Shut down server")
    async def shutdown(self, args):
        asyncio.create_task(self._graceful_shutdown())
    
    @command("drop", "Simulate packet loss: drop <node_id> [on|off|toggle]")
    async def _cmd_drop(self, args):
        if not args:
            print(f"Current drop set: {sorted(self.drop_set)}")
            return
        node_id = args[0]
        mode = args[1] if len(args) > 1 else "toggle" # default to toggle
        if mode == "on":
            self.drop_set.add(node_id)
        elif mode == "off":
            self.drop_set.discard(node_id)
        elif mode == "toggle":
            (self.drop_set.discard if node_id in self.drop_set else self.drop_set.add)(node_id)
        else:
            print("Usage: drop <node_id> [on|off|toggle]")
            return
        logger.info(f"[DROP] {node_id} → {'ON' if node_id in self.drop_set else 'OFF'}")

    @command("delay", "Simulate latency: delay <node_id> <ms|off>")
    async def _cmd_delay(self, args):
        if len(args) < 1:
            print(f"Current delays (ms): { {k:int(v*1000) for k,v in self.delay_map.items()} }")
            return
        node_id = args[0]
        if len(args) == 1 or args[1] == "off": # default to off
            self.delay_map.pop(node_id, None)
            logger.info(f"[DELAY] {node_id} → OFF")
            return
        try:
            ms = int(args[1])
            self.delay_map[node_id] = ms / 1000.0
            logger.info(f"[DELAY] {node_id} → {ms} ms")
        except ValueError:
            print("Usage: delay <node_id> <ms|off>")



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Run server in debug mode (manual STEP)")
    args = parser.parse_args()
    server_config = load_config(section="server")
    host = server_config.get("host", "localhost")
    port = int(server_config.get("port", 5000))
    server = BlockchainServerAsync(host=host, port=port, debug_mode=args.debug)
    asyncio.run(server.start())

