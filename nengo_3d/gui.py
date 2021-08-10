import copy
import json
import logging
import signal
import socket
import struct
import time
from collections import defaultdict
from dataclasses import dataclass
import sys
import subprocess
import os
from typing import *

import nengo
import nengo.utils.progress
import nengo.ensemble
import nengo.utils
# from components import EnhancedJSONEncoder, NengoObjectType, NengoObject, Network

from nengo_3d.gui_backend import Nengo3dServer, Connection
from nengo_3d.name_finder import NameFinder
import nengo_3d.schemas as schemas

script_path = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger(__name__)

message = schemas.Message()


class RequestedProbes(NamedTuple):
    probe: nengo.Probe
    """source object to probe"""
    is_neuron: bool
    """Does this param applies to neurons?"""
    parameter: str
    """Parameter to probe"""


class GuiConnection(Connection):
    def __init__(self, client_socket: socket.socket, addr, server: 'GUI', model: nengo.Network):
        super().__init__(client_socket, addr, server)
        self.server: GUI
        self.requested_probes: dict[nengo.base.NengoObject, list[RequestedProbes]] = defaultdict(list)
        self.model = model
        self.name_finder = NameFinder(terms=self.server.locals, net=model)
        self.sim: nengo.Simulator = None
        """Generate uuid for each model element"""

    def handle_message(self, msg: str):
        super().handle_message(msg)
        self.server: GUI
        try:
            incoming_message: dict = message.loads(msg)
            if incoming_message['schema'] == schemas.NetworkSchema.__name__:
                self.handle_network(incoming_message)
            elif incoming_message['schema'] == schemas.Observe.__name__:
                self.handle_observe(incoming_message)
            elif incoming_message['schema'] == schemas.Simulation.__name__:
                self.handle_simulation(incoming_message)
            elif incoming_message['schema'] == schemas.PlotLines.__name__:
                self.handle_plot_lines(incoming_message)
            else:
                logger.error(f'Unknown schema: {incoming_message["schema"]}')
        except json.JSONDecodeError:
            logger.error(f'Invalid json message: {msg}')
        # except Exception as e:
        #     logger.exception(f'Failed executing: {incoming_message}', exc_info=e)

    def handle_network(self, incoming_message):
        data_scheme = schemas.NetworkSchema(
            context={'name_finder': self.name_finder, 'file': self.server.filename})
        answer = message.dumps({'schema': schemas.NetworkSchema.__name__, 'data': data_scheme.dump(self.model)})
        self.sendall(answer.encode('utf-8'))

    def handle_plot_lines(self, incoming_message):
        schema = schemas.PlotLines()
        plot_lines = schema.load(data=incoming_message['data'])
        parameter = plot_lines['parameter']
        plot_id = plot_lines['plot_id']
        is_neuron = plot_lines['is_neuron']
        obj = self.name_finder.object(name=plot_lines['source'])
        if parameter == 'tuning_curves':
            inputs, activities = nengo.utils.ensemble.tuning_curves(ens=obj, sim=self.sim)
        if parameter == 'response_curves':
            inputs, activities = nengo.utils.ensemble.response_curves(ens=obj, sim=self.sim)
        data_scheme = schemas.PlotLines()
        answer = message.dumps({'schema': schemas.PlotLines.__name__,
                                'data': data_scheme.dump({
                                    **plot_lines,
                                    'x': inputs.tolist(),
                                    'y': activities.tolist()
                                })})
        logger.debug(f'Sending "{parameter}": {plot_id}: {str(answer)[:1000]}')
        self.sendall(answer.encode('utf-8'))

    def handle_observe(self, incoming_message):
        schema = schemas.Observe()
        observe = schema.load(data=incoming_message['data'])
        parameter = observe['parameter']
        is_neuron = observe['neurons']
        obj = self.name_finder.object(name=observe['source'])
        to_probe = obj.neurons if is_neuron else obj
        with self.model:
            probe = nengo.Probe(to_probe, attr=parameter)
        self.requested_probes[obj].append(RequestedProbes(probe, is_neuron, parameter))

    def handle_simulation(self, incoming_message):
        schema = schemas.Simulation()
        sim = schema.load(data=incoming_message['data'])
        if sim['action'] == 'reset':
            del self.sim
            self.sim = None
        elif sim['action'] == 'stop':
            logger.warning('Not implemented')
        elif sim['action'] == 'step':
            if not self.sim:
                self.sim = nengo.Simulator(network=self.model)
            steps = list(range(self.sim.n_steps, sim['until'] + 1))
            if not len(steps) >= 1:
                logger.warning(f'Requested step: {sim["until"]}, but {self.sim.n_steps} is already computed')
                return
            for _ in steps:
                self.sim.step()  # this can be done async
            data_scheme = schemas.SimulationSteps(
                many=True,
                context={'sim': self.sim,
                         'name_finder': self.name_finder,
                         'steps': steps,
                         'requested_probes': self.requested_probes,
                         })
            answer = message.dumps({'schema': schemas.SimulationSteps.__name__,
                                    'data': data_scheme.dump(self.sim.data)})
            logger.debug(f'Sending step {steps}: {str(answer)[:1000]}')
            self.sendall(answer.encode('utf-8'))
        else:
            logger.warning('Unknown field value')

    def sendall(self, msg: bytes):
        self._socket.sendall(struct.pack("i", len(msg)) + msg)


class GUI(Nengo3dServer):
    connection = GuiConnection

    def __init__(self, host: str = 'localhost', port: int = 6001, filename=None, model: Optional[nengo.Network] = None,
                 local_vars: dict[str, Any] = None):
        super().__init__(host, port)
        self.locals = local_vars or {}
        self.model = model
        self.filename = os.path.realpath(filename) or __file__
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
