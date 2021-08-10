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
from nengo_3d_schemas import Message, Observe, Simulation, PlotLines


class SimulationSteps(nengo_3d_schemas.SimulationSteps):
    @pre_dump(pass_many=True)
    def get_parameters(self, sim_data: nengo.simulator.SimulationData, many: bool):
        assert many is True, 'many=False is not supported'
        name_finder: NameFinder = self.context['name_finder']
        sim: nengo.Simulator = self.context['sim']
        steps: list[int] = self.context['steps']
        requested_probes = self.context['requested_probes']
        results = []
        try:
            for step in steps:
                _result = {'step': step, 'parameters': {}, 'neurons_parameters': {}}
                for obj, probes in requested_probes.items():
                    _result['node_name'] = name_finder.name(obj)
                    for probe, is_neuron, parameter in probes:
                        if is_neuron:
                            _result['neurons_parameters'][parameter] = sim_data[probe][step].tolist()
                        else:
                            _result['parameters'][parameter] = sim_data[probe][step].tolist()
                results.append(_result)
        except KeyError as e:
            logging.error(f'No such key: {e}: {list(sim_data.keys())}')
        return results


class ConnectionSchema(nengo_3d_schemas.ConnectionSchema):
    @pre_dump
    def process_connection(self, data: nengo.Connection, **kwargs):
        name_finder = self.context['name_finder']
        result = {'probeable': data.probeable, 'name': name_finder.name(data)}
        for param in data.params:
            result[param] = getattr(data, param)
        result['pre'] = name_finder.name(data.pre)
        result['post'] = name_finder.name(data.post)
        result['size_in'] = data.size_in
        result['size_mid'] = data.size_mid
        result['size_out'] = data.size_out
        result['has_weights'] = data.has_weights
        result['function_info'] = str(data.function_info)
        result['solver'] = str(data.solver)
        result['synapse'] = str(data.synapse)
        result['transform'] = str(data.transform)
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

        result['size_in'] = data.size_in
        result['size_out'] = data.size_out
        result['n_neurons'] = getattr(data, 'n_neurons', None)
        result['neurons'] = getattr(data, 'neurons', None)
        if getattr(data, 'neuron_type', None):
            result['neuron_type'] = {
                'name': str(data.neuron_type),
                'negative': data.neuron_type.negative,
                'spiking': data.neuron_type.spiking,
                'probeable': data.neuron_type.probeable,
            }
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
