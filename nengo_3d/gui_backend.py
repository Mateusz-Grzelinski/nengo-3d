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
from dataclasses import dataclass
from typing import *

logger = logging.getLogger(__file__)


@dataclass
class GuiServerSettings:
    address: str = "localhost"
    port: int = 7000


class Connection(threading.Thread):
    def __init__(self, client_socket: socket.socket, addr, server_socket: 'Nengo3dServer'):
        super().__init__()
        self.server_socket = server_socket
        self.socket = client_socket
        self.addr = addr
        self.running = True

        self.to_send: Optional[str] = None

    def run(self) -> None:
        self.socket.setblocking(True)
        try:
            while self.running:
                msg = self.socket.recv(1024)
                if msg:
                    self.handle_message(msg)
                    continue
                # if self.to_send:
                #     self.socket.sendall(data=self.to_send.encode('utf-8'))
                #     self.to_send = None
                #     continue
                time.sleep(0.1)
        except (ConnectionAbortedError, ConnectionResetError) as e:
            logger.warning(e)
        self.socket.close()
        self.server_socket.remove(self)

    def handle_message(self, msg: bytes) -> None:
        logger.debug(f'{self.addr} incoming: {msg.decode("utf-8")}')

    # def send(self, message: str):
    #     if self.to_send:
    #         logger.error('errorrr!!')
    #     self.to_send = message

    def stop(self):
        self.running = False


class Nengo3dServer:
    _running = True
    connection = Connection

    def __init__(self, host: str, port: int):
        self.port = port
        self.host = host
        self.connections = []

    @classmethod
    def exit_gracefully(cls, sig, frame) -> None:
        logger.info(f'Terminating server after signal: {sig}')
        Nengo3dServer._running = False

    def remove(self, connection) -> None:
        # todo probably requires a lock
        self.connections.remove(connection)

    def run(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.host, self.port))
        sock.setblocking(0)
        sock.listen(1000)

        # for faster TIME_WAIT
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        logger.info("Listening on port % s", self.port)

        while Nengo3dServer._running:
            try:
                timeout = 0.1  # Check for a new client every 10th of a second
                readable, _, _ = select.select([sock], [], [], timeout)
                if len(readable) > 0:
                    for connection in self.connections:
                        if not connection.is_alive():
                            logger.warning(f'dead thread: {connection}')
                    client_socket, client_address = sock.accept()
                    non_blocking_connection = self.connection(client_socket, addr=client_address, server_socket=self)
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
    parser = argparse.ArgumentParser(description="Start broadcasting server for Mixer")
    # add_logging_cli_args(parser)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args(), parser


if __name__ == "__main__":
    args, args_parser = parse_cli_args()
    server = Nengo3dServer(host='localhost', port=args.port)
    server.run()
