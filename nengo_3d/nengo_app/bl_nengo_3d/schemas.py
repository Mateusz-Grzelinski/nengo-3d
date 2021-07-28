from marshmallow import post_load
import networkx as nx

import nengo_3d_schemas
from nengo_3d_schemas import Message, Observe, SimulationSteps, Simulation


class NetworkSchema(nengo_3d_schemas.NetworkSchema):
    @post_load
    def make_user(self, data: dict, **kwargs) -> nx.DiGraph:
        g = nx.DiGraph()
        nodes = data.pop('nodes')
        for node_name, attributes in nodes.items():
            g.add_node(node_name,
                       probeable=attributes['probeable'],
                       type=attributes['type'],
                       label=attributes['label'])
        connections = data.pop('connections')
        for conn_name, attributes in connections.items():
            g.add_edge(attributes['pre'], attributes['post'])
            g[attributes['pre']][attributes['post']]['label'] = attributes['label']
        return g, data
