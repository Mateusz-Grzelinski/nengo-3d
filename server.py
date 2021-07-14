import os
import signal
import subprocess
import sys
import logging
import argparse
import select
import threading
import time
import socket
import queue
from dataclasses import dataclass

try:
    import bpy
except ImportError:
    print('This script must be run from blender')

# blender_path = r'C:\Users\mat-lp\Documents\magisterka\blender-2.92.0-windows64\blender.exe'

# os.system(f'{blender_path} --log "bke.appdir.*" --log-level -1 --app-template ./nengo_startup.py')
# os.system(f'{blender_path} ./blender_template/startup.blend')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


@dataclass
class GuiServerSettings:
    address: str = "localhost"
    port: int = 7000


class Connection(threading.Thread):
    def __init__(self, socket: socket.socket, addr):
        super().__init__()
        self.socket = socket
        self.addr = addr
        self.running = True

    def run(self) -> None:
        self.socket.setblocking(True)
        try:
            while self.running:
                msg = self.socket.recv(1024)
                if not msg:
                    time.sleep(0.1)
                    continue
                logger.debug(f'{self.addr} incoming: {msg.decode("utf-8")}')
                time.sleep(0.1)
        except ConnectionAbortedError as e:
            logger.exception(e)
        self.socket.close()

    def stop(self):
        self.running = False


class Server:
    _running = True

    def __init__(self):
        self.connections = []

    @classmethod
    def exit_gracefully(cls, sig, frame):
        logger.info(f'Terminating server after signal: {sig}')
        Server._running = False

    def run(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        binding_host = "localhost"
        sock.bind((binding_host, port))
        sock.setblocking(0)
        sock.listen(1000)

        # for faster TIME_WAIT
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        logger.info("Listening on port % s", port)

        while Server._running:
            try:
                timeout = 0.1  # Check for a new client every 10th of a second
                readable, _, _ = select.select([sock], [], [], timeout)
                if len(readable) > 0:
                    client_socket, client_address = sock.accept()
                    non_blocking_connection = Connection(client_socket, addr=client_address)
                    non_blocking_connection.run()
                    self.connections.append(non_blocking_connection)
                    logger.info(f"New connection from {client_address}, all connections: {len(self.connections)}")
            except KeyboardInterrupt:
                break

        for connection in self.connections:
            connection: Connection
            connection.stop()
            connection.join()
        logger.info("Shutting down server")
        sock.close()


signal.signal(signal.SIGINT, Server.exit_gracefully)
signal.signal(signal.SIGTERM, Server.exit_gracefully)
signal.signal(signal.SIGBREAK, Server.exit_gracefully)


def parse_cli_args():
    DEFAULT_PORT = 6001
    parser = argparse.ArgumentParser(description="Start broadcasting server for Mixer")
    # add_logging_cli_args(parser)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args(), parser


if __name__ == "__main__":
    args, args_parser = parse_cli_args()
    server = Server()
    server.run(args.port)
