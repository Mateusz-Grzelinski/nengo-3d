import json
import logging
import signal
import socket
import time
from dataclasses import dataclass
import sys
import subprocess
import os
from typing import *

import nengo
import nengo.utils.progress
# from components import EnhancedJSONEncoder, NengoObjectType, NengoObject, Network

from nengo_3d.gui_backend import Nengo3dServer, Connection
from nengo_3d.name_finder import NameFinder
from nengo_3d.schemas import NetworkSchema

blender_path = r'E:\PycharmProjects\nengo_3d_thesis\blender-2.93.1-windows-x64\blender.exe'
script_path = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__file__)


class GuiConnection(Connection):
    def handle_message(self, msg: bytes):
        super().handle_message(msg)
        self.server_socket: GUI
        msg = msg.decode('utf-8')
        try:
            d: dict = json.loads(msg)
        except json.JSONDecodeError:
            logger.warning(f'Invalid json message: {msg}')
            pass
        else:
            if d.get('model'):
                net = self.server_socket.get_model()
                self.socket.sendall(net.encode('utf-8'))
                # self.socket.sendall(json.dumps(net, cls=EnhancedJSONEncoder).encode('utf-8'))


class GUI(Nengo3dServer):
    connection = GuiConnection

    def __init__(self, host: str = 'localhost', port: int = 6001, filename=None, model: Optional[nengo.Network] = None,
                 local_vars: dict[str, Any] = None, editor=True):
        super().__init__(host, port)
        self.locals = local_vars or {}
        self.model = model
        self.filename = filename or __file__

        self.model_names = NameFinder(terms=self.locals, net=self.model)
        """Generate uuid for each model element"""

        # self.blender_log = None
        self._blender_subprocess = None

    def start(self, skip_blender=False) -> None:
        # os.makedirs('log', exist_ok=True)
        blender_template = os.path.join(script_path, 'blender_template', 'startup.blend')
        if not skip_blender:
            # self.blender_log = open('log/blender.log', 'w')
            from nengo_3d import BLENDER_PIP_MODULES_PATH
            self._blender_subprocess = subprocess.Popen([blender_path,
                                                         '--engine', 'BLENDER_WORKBENCH',
                                                         '--python-expr',
                                                         f'import sys; sys.path.append({repr(BLENDER_PIP_MODULES_PATH)})',
                                                         '--addons', 'bl_nengo_3d', blender_template],
                                                        # stdout=self.blender_log, stderr=self.blender_log,
                                                        # env=os.environ
                                                        )
        self.run()
        if not skip_blender:
            e = self._blender_subprocess.wait()
            logger.info(f'blender finished with code: {e}')
            # self.blender_log.close()

    def get_model(self) -> str:
        m = NetworkSchema(name_finder=self.model_names)
        return m.dumps(self.model)

    def start_sim(self):
        nengo.utils.progress.ProgressBar
        sim = nengo.Simulator(network=self.model)
        sim.step()
        sim.data.keys()
        sim.n_steps


if __name__ == '__main__':
    model = nengo.Network()
    g = GUI()
    # time.sleep(3)
    g.start()
