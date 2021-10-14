import os
import signal
import struct
import subprocess
import sys
import logging
import argparse
import select
import threading
import time
import socket
from dataclasses import dataclass
from typing import *

logger = logging.getLogger(__file__)


@dataclass
class GuiServerSettings:
    address: str = "localhost"
    port: int = 7000


class Connection(threading.Thread):
    def __init__(self, client_socket: socket.socket, addr, server: 'Nengo3dServer', **kwargs):
        super().__init__()
        self.server = server
        self._socket = client_socket
        self.addr = addr
        self.running = True

        self.to_send: Optional[str] = None

    def run(self) -> None:
        self._socket.setblocking(True)
        try:
            while self.running:
                size_raw = self._socket.recv(struct.calcsize("i"))
                if not size_raw:
                    break
                size = struct.unpack("i", size_raw)[0]
                data = ""
                while len(data) < size:
                    msg = self._socket.recv(size - len(data))
                    if not msg:
                        return None
                    data += msg.decode('utf-8')
                    logger.debug(f'Incoming: {data}')
                    self.handle_message(data)
        except (ConnectionAbortedError, ConnectionResetError) as e:
            logger.warning(e)
        else:
            self._socket.close()
        finally:
            self.server.remove(self)

    def handle_message(self, msg: str) -> None:
        logger.debug(f'{self.addr} incoming: {msg[:1000]}')

    def stop(self):
        self.running = False


class Nengo3dServer:
    stop_now = False
    connection = Connection

    def __init__(self, host: str, port: int):
        self.port = port
        self.host = host
        self.connections = []
        self._running = True

    @classmethod
    def exit_gracefully(cls, sig, frame) -> None:
        logger.info(f'Terminating server after signal: {sig}')
        cls.stop_now = False

    def remove(self, connection: Connection) -> None:
        # todo probably requires a lock
        self.connections.remove(connection)
        if not self.connections:
            logger.info('No connections remaining')
            # self._running = False

    def run(self, connection_init_args=None) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.host, self.port))
        sock.setblocking(False)
        sock.listen(10)

        # for faster TIME_WAIT
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        logger.info("Listening on port % s", self.port)

        while self._running and not self.stop_now:
            try:
                timeout = 0.1  # Check for a new client every 10th of a second
                readable, _, _ = select.select([sock], [], [], timeout)
                if len(readable) > 0:
                    client_socket, client_address = sock.accept()
                    non_blocking_connection = self.connection(client_socket, addr=client_address, server=self,
                                                              **connection_init_args)
                    non_blocking_connection.start()
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


signal.signal(signal.SIGINT, Nengo3dServer.exit_gracefully)
signal.signal(signal.SIGTERM, Nengo3dServer.exit_gracefully)
signal.signal(signal.SIGBREAK, Nengo3dServer.exit_gracefully)


def parse_cli_args():
    DEFAULT_PORT = 6001
    parser = argparse.ArgumentParser(description="Start broadcasting server for Nengo 3d")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args(), parser


if __name__ == "__main__":
    args, args_parser = parse_cli_args()
    server = Nengo3dServer(host='localhost', port=args.port)
    server.run()
