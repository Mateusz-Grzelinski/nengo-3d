import logging
from itertools import chain
from typing import Union, Optional

import nengo
import nengo.spa.module

from marshmallow import pre_dump

import nengo_3d.nengo_3d_schemas as nengo_3d_schemas
from nengo_3d.name_finder import NameFinder
from nengo_3d.nengo_3d_schemas import Message, Observe, Simulation, PlotLines

Message = Message
Observe = Observe
Simulation = Simulation
PlotLines = PlotLines


class SimulationSteps(nengo_3d_schemas.SimulationSteps):
    @pre_dump(pass_many=True)
    def get_parameters(self, sim_data: nengo.simulator.SimulationData, many: bool):
        assert many is True, 'many=False is not supported'
        name_finder: NameFinder = self.context['name_finder']
        sim: nengo.Simulator = self.context['sim']
        model: nengo.Network = self.context['model']
        vocab: dict[nengo.base.NengoObject, nengo.spa.Vocabulary] = self.context['vocab']
        recorded_steps: list[int] = self.context['recorded_steps']
        sample_every: int = self.context['sample_every']
        requested_probes: dict[nengo.base.NengoObject, list['RequestedProbes']] = self.context['requested_probes']
        results = []
        try:
            for step in recorded_steps:
                step = int(step / sample_every)
                for obj, probes in requested_probes.items():
                    _result = {'step': step, 'parameters': {}, 'node_name': name_finder.name(obj)}
                    for probe, access_path, _, _ in probes:
                        probe: nengo.Probe
                        # sim.trange()
                        # logging.debug((probe, recorded_steps, step, sample_every, len(sim_data[probe])))
                        if access_path.endswith('similarity'):
                            _vocab = vocab.get(probe.obj)
                            _vocab2 = vocab.get(probe.obj.size_out)
                            if _vocab:
                                # legacy version
                                _result['parameters'][access_path] = nengo.spa.similarity(data=sim_data[probe][step],
                                                                                          vocab=_vocab)[0].tolist()
                            elif _vocab2:
                                # nengo_spa version
                                import nengo_spa
                                _result['parameters'][access_path] = nengo_spa.similarity(data=sim_data[probe][step],
                                                                                          vocab=_vocab2).tolist()
                            else:
                                assert False
                        else:
                            _result['parameters'][access_path] = sim_data[probe][step].tolist()
                    results.append(_result)
        except KeyError as e:
            logging.error(f'No such key: {e}: {list(sim_data.keys())}')
        return results


class ConnectionSchema(nengo_3d_schemas.ConnectionSchema):
    @pre_dump
    def process_connection(self, data: nengo.Connection, **kwargs):
        assert isinstance(data, nengo.Connection), data
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

        result.update({'type': 'Connection',
                       'class_type': type(data).__name__})
        return result


class NodeSchema(nengo_3d_schemas.NodeSchema):
    @pre_dump
    def process_node(self, data: nengo.Node, **kwargs):
        vocabulary: Optional[nengo.spa.Vocabulary] = self.context['vocabulary']
        vocab_keys = []
        if vocabulary:
            if isinstance(vocabulary.keys, list):
                vocab_keys = vocabulary.keys
            else:
                vocab_keys = list(vocabulary.keys())

        result = {'probeable': data.probeable,
                  'class_type': type(data).__name__,
                  'name': self.context['name'],
                  'network_name': self.context['network_name'],
                  'parent_network': self.context['network_name'],  # same as above
                  'module': self.context['module'],
                  'has_vocabulary': bool(vocabulary),
                  'vocabulary_size': len(vocabulary.vectors) if vocabulary else None,
                  'vocabulary': vocab_keys,
                  }
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
        file = self.context.get('file')
        name_finder = self.context['name_finder']
        parent_network = self.context['parent_network']
        network_name = name_finder.name(data)
        module: str = self.context['module']
        vocab = self.context['vocab']
        vocab_v2 = self.context['vocab_v2']
        modules: dict = self.context.pop('modules') if self.context.get('modules') else {}
        result = {
            'nodes': {},
            'connections': {},
            'networks': {},
            'file': file,
            'network_name': network_name,
            'parent_network': parent_network,
            'module': module,
            'n_neurons': data.n_neurons,
            'type': 'Network',
            'class_type': type(data).__name__
        }

        for obj in chain(data.ensembles, data.nodes):
            obj: Union[nengo.Ensemble, nengo.Node]
            _vocab: nengo.spa.Vocabulary = vocab.get(obj)
            if not _vocab:
                _vocab = vocab_v2.get(obj.size_in)  # todo can be also size_out
            name = name_finder.name(obj)
            s = NodeSchema(
                context={'network_name': network_name, 'module': module,
                         'vocabulary': _vocab, 'name': name,
                         }
            )
            result['nodes'][name] = s.dump(obj)

        for obj in data.networks:
            obj: nengo.Network
            subnet_name = name_finder.name(obj)
            context = self.context.copy()
            context['parent_network'] = network_name
            context['module'] = obj.label if obj.label in modules.keys() else module
            s = NetworkSchema(context=context)
            result['networks'][subnet_name] = s.dump(obj)

        s = ConnectionSchema(context={'name_finder': name_finder})
        for obj in data.all_connections:  # connections between networks are only in "all_connections"
            result['connections'][name_finder.name(obj)] = s.dump(obj)
        return result
