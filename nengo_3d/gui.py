import copy
import json
import logging
import signal
import socket
import time
from collections import defaultdict
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
from nengo_3d import schemas

script_path = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger(__name__)


class GuiConnection(Connection):
    def __init__(self, client_socket: socket.socket, addr, server: 'GUI', model: nengo.Network):
        super().__init__(client_socket, addr, server)
        self.server: GUI
        self.requested_probes: dict[nengo.base.NengoObject, list[tuple[nengo.Probe, str]]] = defaultdict(list)
        self.model = model
        self.name_finder = NameFinder(terms=self.server.locals, net=model)
        self.sim: nengo.Simulator = None
        """Generate uuid for each model element"""

    def get_model(self) -> dict:
        """Returns `schemas.NetworkSchema`"""
        m = schemas.NetworkSchema(name_finder=self.name_finder)
        return m.dump(self.model)

    def start_sim(self):
        """Returns `schemas.SimulationSteps`"""
        # nengo.utils.progress.ProgressBar
        self.sim = nengo.Simulator(network=self.model)
        self.sim.data.keys()
        self.sim.reset()
        return self.sim.step()

    def handle_message(self, msg: bytes):
        super().handle_message(msg)
        self.server: GUI
        msg = msg.decode('utf-8')
        message = schemas.Message()
        try:
            incoming_message: dict = message.loads(msg)
            if incoming_message['schema'] == schemas.NetworkSchema.__name__:
                net = self.get_model()
                answer = message.dumps({'schema': schemas.NetworkSchema.__name__, 'data': net})
                self.socket.sendall(answer.encode('utf-8'))
            elif incoming_message['schema'] == schemas.Observe.__name__:
                schema = schemas.Observe()
                observe = schema.load(data=incoming_message['data'])
                parameter = observe['parameter']  # todo
                obj = self.name_finder.object(name=observe['source'])
                with self.model:
                    probe = nengo.Probe(obj, attr=parameter)
                self.requested_probes[obj].append((probe, parameter))  # ??
            elif incoming_message['schema'] == schemas.Simulation.__name__:
                schema = schemas.Simulation()
                sim = schema.load(data=incoming_message['data'])
                if sim['action'] == 'start':
                    logger.warning('Not implemented')
                elif sim['action'] == 'stop':
                    logger.warning('Not implemented')
                elif sim['action'] == 'step':
                    if not self.sim:
                        self.start_sim()
                    self.sim.step()  # this can be done async
                    data_scheme = schemas.SimulationSteps(many=True)
                    data_scheme.context['model'] = self.model
                    data_scheme.context['name_finder'] = self.name_finder
                    data_scheme.context['steps'] = (self.sim.n_steps - 1, )
                    data_scheme.context['requested_probes'] = self.requested_probes
                    data = data_scheme.dump(self.sim.data)
                    # logger.debug(data_scheme.validate(self.sim.data))
                    answer = message.dumps({'schema': schemas.SimulationSteps.__name__,
                                            'data': data})
                    logger.debug(f'Sending step {self.sim.n_steps - 1}: {answer}')
                    self.socket.sendall(answer.encode('utf-8'))
                else:
                    logger.warning('Unknown field value')
            else:
                logger.error(f'Unknown schema: {incoming_message["schema"]}')
        except json.JSONDecodeError:
            logger.error(f'Invalid json message: {msg}')
        # except Exception as e:
        #     logger.exception(f'Failed executing: {incoming_message}', exc_info=e)


class GUI(Nengo3dServer):
    connection = GuiConnection

    def __init__(self, host: str = 'localhost', port: int = 6001, filename=None, model: Optional[nengo.Network] = None,
                 local_vars: dict[str, Any] = None):
        super().__init__(host, port)
        self.locals = local_vars or {}
        self.model = model
        self.filename = filename or __file__
        # self.blender_log = None
        self._blender_subprocess = None

    def start(self, skip_blender=False) -> None:
        # os.makedirs('log', exist_ok=True)
        blender_template = os.path.join(script_path, 'nengo_app', 'startup.blend')
        if not skip_blender:
            # self.blender_log = open('log/blender.log', 'w')
            from nengo_3d import BLENDER_EXE_PATH
            # import pygetwindow
            command = [BLENDER_EXE_PATH,
                       '--engine', 'BLENDER_WORKBENCH',
                       '--app-template', 'nengo_app',
                       '--window-geometry', '-1920', '0', '1920', '1080',
                       # '--no-window-focus',
                       # '--python-expr',
                       # f'import sys; sys.path.append({repr(BLENDER_PIP_MODULES_PATH)})',
                       # '--addons', 'bl_nengo_3d',
                       blender_template,
                       ]
            # stdout=self.blender_log, stderr=self.blender_log,
            logging.info(f'Launching: {" ".join(command)}')
            self._blender_subprocess = subprocess.Popen(command, env=os.environ)
        self.run(connection_init_args={'model': self.model})
        if not skip_blender:
            e = self._blender_subprocess.wait()
            logger.info(f'blender finished with code: {e}')
            # self.blender_log.close()


if __name__ == '__main__':
    model = nengo.Network()
    g = GUI()
    # time.sleep(3)
    g.start()
