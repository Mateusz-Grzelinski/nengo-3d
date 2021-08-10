import logging

from marshmallow import post_load, pre_dump
import networkx as nx

import nengo_3d_schemas
from nengo_3d_schemas import Message, Observe, SimulationSteps, Simulation


class PlotLines(nengo_3d_schemas.PlotLines):
    @pre_dump
    def process_axes(self, data: 'Axes', **kwargs):
        ax = data
        node = self.context['node']
        is_neuron = self.context['is_neuron']
        result = {'plot_id': ax.root.name, 'source': node.name, 'parameter': ax.parameter, 'is_neuron': is_neuron,
                  'x': [], 'y': []}
        return result


class NetworkSchema(nengo_3d_schemas.NetworkSchema):
    @post_load
    def make_user(self, data: dict, **kwargs) -> nx.DiGraph:
        g = nx.DiGraph()
        nodes = data.pop('nodes')
        for node_name, attributes in nodes.items():
            g.add_node(node_name)
            for attr_name, attr in attributes.items():
                g.nodes[node_name][attr_name] = attr
        connections = data.pop('connections')
        for conn_name, attributes in connections.items():
            # todo conn_name is ignored...
            g.add_edge(attributes['pre'], attributes['post'])
            # g[attributes['pre']][attributes['post']]['label'] = attributes['label']
            for attr_name, attr in attributes.items():
                g.edges[attributes['pre'], attributes['post']][attr_name] = attr
        return g, data
