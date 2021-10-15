import json
import logging
import socket
import struct
from collections import defaultdict
import subprocess
import os
from typing import *

import nengo
import nengo.spa.module
import nengo.utils.progress
import nengo.ensemble
import nengo.utils

import nengo_3d.utils
import numpy as np
from nengo_3d import dependencies
from nengo_3d.gui_backend import Nengo3dServer, Connection
from nengo_3d.name_finder import NameFinder
import nengo_3d.schemas as schemas

script_path = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger(__name__)

message = schemas.Message()


class ScheduledPlot(NamedTuple):
    source: str
    access_path: str
    step: int
    to_plot: nengo.base.NengoObject


class RequestedProbes(NamedTuple):
    probe: nengo.Probe
    """source object to probe"""
    access_path: str
    to_probe: Any
    attribute: str
    # vocabulary: Optional[nengo.spa.Vocabulary]


class GuiConnection(Connection):
    def __init__(self, client_socket: socket.socket, addr, server: 'GUI', model: nengo.Network):
        super().__init__(client_socket, addr, server)
        self.vocab = {}
        self.vocab_v2 = {}
        self.server: GUI
        self.scheduled_plots: dict[int, list[ScheduledPlot]] = defaultdict(list)
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
            data = incoming_message.get('data') or {}
            if incoming_message['schema'] == schemas.NetworkSchema.__name__:
                self.handle_network(data)
            elif incoming_message['schema'] == schemas.Observe.__name__:
                self.handle_observe(data)
            elif incoming_message['schema'] == schemas.Simulation.__name__:
                self.handle_simulation(data)
            elif incoming_message['schema'] == schemas.PlotLines.__name__:
                self.handle_plot_lines(data)
            else:
                logger.error(f'Unknown schema: {incoming_message["schema"]}')
        except json.JSONDecodeError:
            logger.error(f'Invalid json message: {msg}')
        except Exception as e:
            logger.exception(f'Failed executing: {msg}', exc_info=e)

    def handle_network(self, incoming_message):
        if isinstance(self.model, nengo.spa.SPA):  # legacy nengo.spa
            for dim, module in self.model._modules.items():
                module: nengo.spa.module.Module
                for node, _vocab in module.inputs.values():
                    assert self.vocab.get(node) is None
                    self.vocab[node] = _vocab
                for node, _vocab in module.outputs.values():
                    assert self.vocab.get(node) is None
                    self.vocab[node] = _vocab
        elif hasattr(self.model, 'vocabs'):  # nengo_spa implementation
            import nengo_spa
            nengo_spa.vocabulary
            for dim, value in self.model.vocabs.items():
                assert self.vocab_v2.get(dim) is None
                self.vocab_v2[dim] = value
        data_scheme = schemas.NetworkSchema(
            context={'name_finder': self.name_finder, 'file': self.server.filename, 'parent_network': '', 'module': '',
                     'modules': getattr(self.model, '_modules', []), 'vocab': self.vocab, 'vocab_v2': self.vocab_v2})
        answer = message.dumps({'schema': schemas.NetworkSchema.__name__, 'data': data_scheme.dump(self.model)})
        self.sendall(answer.encode('utf-8'))

    def handle_plot_lines(self, incoming_message: dict):
        schema = schemas.PlotLines()
        plot_lines = schema.load(data=incoming_message)
        access_path = plot_lines['access_path']
        step = plot_lines['step']
        source = plot_lines['source']
        obj = self.name_finder.object(name=source)
        self.scheduled_plots[step].append(ScheduledPlot(source, access_path, step, obj))

    def handle_observe(self, incoming_message):
        schema = schemas.Observe()
        observe = schema.load(data=incoming_message)
        access_path = observe['access_path'].split('.')
        sample_every = observe['sample_every']
        # module = observe['module']
        dt = observe['dt']
        obj = self.name_finder.object(name=observe['source'])
        # todo avoid duplicated probes
        if 'probeable' in access_path:
            # special case is probeable values
            if access_path[-1] == 'similarity':
                access_path.pop()
                use_similarity = True
            else:
                use_similarity = False

            to_probe = nengo_3d.utils.get_value(obj, access_path[:-2])
            attr = access_path[-1]
            if not hasattr(to_probe, 'probeable'):
                logger.warning(f'{to_probe} ({access_path}) does not have field "probeable"')
                return
            if to_probe and attr in to_probe.probeable:
                # Ensemble, Neurons, Node, or Connection
                if not isinstance(to_probe, (nengo.Ensemble, nengo.Node, nengo.Connection, nengo.ensemble.Neurons)):
                    logger.error(f'Incompatible type {to_probe}: {type(to_probe)}')
                    return

                if use_similarity:
                    self.model: nengo.spa.SPA
                    if self.vocab.get(obj) is None and self.vocab_v2.get(obj.size_out) is None:
                        logger.error(
                            f'Can not compute similarity for {to_probe} - there is no vocabulary associated with it')
                        return

                with self.model:
                    probe = nengo.Probe(to_probe, attr=attr, sample_every=sample_every * dt,
                                        synapse=None)  # todo check data shape

                rp = RequestedProbes(probe, observe['access_path'], to_probe, attr)
                logger.debug(f'Added to observation: {rp}')
                self.requested_probes[obj].append(rp)
        else:
            # todo observe built in values?
            # paths = list(get_path(obj, access_path))
            # assert len(paths) == len(access_path), (paths, access_path)
            logger.warning(f'Not supported yet: {observe}')

    def handle_simulation(self, incoming_message):
        schema = schemas.Simulation()
        sim = schema.load(data=incoming_message)
        dt = sim['dt']
        if sim['action'] == 'reset':
            del self.sim
            self.sim = None
            observes = sim['observe']
            for probes in self.requested_probes.values():
                for probe in probes:
                    self.model.all_probes.remove(probe.probe)
            self.requested_probes.clear()
            for observe in observes:
                self.handle_observe(observe)
            plot_lines = sim['plot_lines']
            self.scheduled_plots.clear()
            for plot in plot_lines:
                self.handle_plot_lines(plot)
        elif sim['action'] == 'stop':
            logger.warning('Not implemented')
        elif sim['action'] == 'step':
            if not self.sim:
                self.sim = nengo.Simulator(network=self.model, dt=dt)

            until = sim['until'] - sim['until'] % sim['sample_every']
            steps = list(range(self.sim.n_steps, until))
            if not len(steps) >= 1:
                logger.warning(f'Requested step: {sim["until"]}, but {self.sim.n_steps} is already computed')
                return
            for s in steps:
                self._handle_scheduled_plots(s)
                self.sim.step()  # todo this can be done async
            sample_every = sim['sample_every']
            assert sample_every > 0, sim
            if sample_every != 1:
                recorded_steps = steps[::sample_every]  # todo
            else:
                recorded_steps = steps
            data_scheme = schemas.SimulationSteps(
                many=True,
                context={'sim': self.sim,
                         'model': self.model,
                         'vocab': self.vocab if self.vocab else self.vocab_v2,
                         'name_finder': self.name_finder,
                         'recorded_steps': recorded_steps,
                         'sample_every': sample_every,
                         'requested_probes': self.requested_probes,
                         })
            answer = message.dumps({'schema': schemas.SimulationSteps.__name__,
                                    'data': data_scheme.dump(self.sim.data)})
            logger.debug(f'Sending step {list(nengo_3d.utils.ranges_str(steps))}: {str(answer)[:1000]}')
            self.sendall(answer.encode('utf-8'))
        else:
            logger.warning('Unknown field value')

    def _handle_scheduled_plots(self, step):
        plots = self.scheduled_plots.get(step)
        if not plots:
            return
        for plot in plots:
            access_path = plot.access_path
            if access_path == 'neurons.tuning_curves':
                inputs, activities = nengo.utils.ensemble.tuning_curves(ens=plot.to_plot, sim=self.sim)
            elif access_path == 'neurons.response_curves':
                inputs, activities = nengo.utils.ensemble.response_curves(ens=plot.to_plot, sim=self.sim)
            else:
                logger.error('This should not happen')
                continue
            data_scheme = schemas.PlotLines()
            data = {
                'source': plot.source,
                'access_path': plot.access_path,
                'step': plot.step,
                'data': np.append(np.reshape(inputs, newshape=(len(inputs), 1)), activities, axis=1).tolist(),
                # np.append(inputs, activities).tolist()
                # 'x': inputs.tolist(),
                # 'y': activities.tolist()
            }
            answer = message.dumps({'schema': schemas.PlotLines.__name__,
                                    'data': data_scheme.dump(data)})
            logger.debug(f'Sending "{access_path}": {plot.source} at {plot.step}: {str(answer)[:1000]}')
            self.sendall(answer.encode('utf-8'))

    def sendall(self, msg: bytes):
        self._socket.sendall(struct.pack("i", len(msg)) + msg)


class GUI(Nengo3dServer):
    connection = GuiConnection

    def __init__(self, host: str = 'localhost', port: int = 6001, filename=None, model: Optional[nengo.Network] = None,
                 local_vars: dict[str, Any] = None, blender_exe: str = 'blender.exe'):
        super().__init__(host, port)
        self.blender_exe = blender_exe
        self.locals = local_vars or {}
        if isinstance(model, nengo.spa.SPA):
            nengo.spa.enable_spa_params(model)
        self.model = model
        self.filename = os.path.realpath(filename) or __file__
        # self.blender_log = None
        self._blender_subprocess = None

    def start(self, skip_blender=False) -> None:
        dependencies.install(self.blender_exe)
        # from nengo_3d import BLENDER_EXE_PATH
        # os.makedirs('log', exist_ok=True)
        # blender_template = os.path.join(script_path, 'nengo_app', 'startup.blend')
        if not skip_blender:
            # self.blender_log = open('log/blender.log', 'w')
            command = [self.blender_exe,
                       # '--engine', 'EEVEE',
                       '--app-template', 'nengo_app',
                       # '--window-geometry', '-1920', '0', '1920', '1080',
                       # '--no-window-focus',
                       # '--python-expr',
                       # f'import sys; sys.path.append({repr(BLENDER_PIP_MODULES_PATH)})',
                       # '--addons', 'bl_nengo_3d',
                       # blender_template,
                       ]
            blend_file = os.path.splitext(self.filename)[0] + '.blend'
            if os.path.exists(blend_file):
                command.append(blend_file)
                logger.info(f'Using saved file: {blend_file}')
            # stdout=self.blender_log, stderr=self.blender_log,
            logging.info(f'Staring GUI: {" ".join(command)}')
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
