import logging
import typing
# from typing import *
from itertools import chain
import nengo
import numpy as np
from marshmallow import pre_dump, types

from nengo_3d.name_finder import NameFinder
import sys

sys.path.append("..")  # Adds higher directory to python modules path to import nengo_3d_schemas
import nengo_3d_schemas
from nengo_3d_schemas import Message, Observe, Simulation


class SimulationSteps(nengo_3d_schemas.SimulationSteps):
    @pre_dump(pass_many=True)
    def get_parameters(self, sim_data: nengo.simulator.SimulationData, many: bool):
        assert many is True, 'many=False is not supported'
        name_finder: NameFinder = self.context['name_finder']
        model: nengo.Network = self.context['model']
        steps: list[int] = self.context['steps']
        requested_probes = self.context['requested_probes']
        result = []
        try:
            for step in steps:
                for obj, probes in requested_probes.items():
                    _result = {'node_name': name_finder.name(obj), 'step': step, 'parameters': {}}
                    for probe, parameter in probes:
                        _result['parameters'][parameter] = list(sim_data[probe][step])
                    result.append(_result)
        except KeyError as e:
            logging.error(f'{e}: {list(sim_data.keys())}')
        return result


# val = '{\'parameters\': {1: {(\'ens\', \'decoded_output\'): [0.19893262191626648, -0.11674964730659484]}}}'
# val = {'parameters': {1: {('ens', 'decoded_output'): [0.19893262191626648, -0.11674964730659484]}}}
# s = SimulationSteps()
# print(s.dumps(val))

class ConnectionSchema(nengo_3d_schemas.ConnectionSchema):
    @pre_dump
    def process_connection(self, data: nengo.Connection, **kwargs):
        name_finder = self.context['name_finder']
        result = {'probeable': data.probeable, 'name': name_finder.name(data)}
        for param in data.params:
            result[param] = getattr(data, param)
        result['pre'] = name_finder.name(data.pre)
        result['post'] = name_finder.name(data.post)
        return result


class NodeSchema(nengo_3d_schemas.NodeSchema):
    @pre_dump
    def process_node(self, data: nengo.Node, **kwargs):
        result = {'probeable': data.probeable}
        for param in data.params:
            result[param] = getattr(data, param)
        if isinstance(data, nengo.Node):
            result['type'] = 'Node'
        elif isinstance(data, nengo.Ensemble):
            result['type'] = 'Ensemble'
        elif isinstance(data, nengo.Network):
            result['type'] = 'Network'
        else:
            result['type'] = 'UNKNOWN'

        # for param in data.params:
        #     result[param] = getattr(data, param)

        return result


class NetworkSchema(nengo_3d_schemas.NetworkSchema):
    @pre_dump
    def process_network(self, data: nengo.Network, **kwargs):
        """Give name to network"""
        file = self.context['file']
        result = {'nodes': {}, 'connections': {}, 'file': file, 'n_neurons': data.n_neurons}
        name_finder = self.context['name_finder']
        s = NodeSchema()
        for obj in chain(data.ensembles, data.nodes):
            result['nodes'][name_finder.name(obj)] = s.dump(obj)
        s = ConnectionSchema(context={'name_finder': name_finder})
        for obj in data.connections:
            result['connections'][name_finder.name(obj)] = s.dump(obj)
        return result
