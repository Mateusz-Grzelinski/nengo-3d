from dataclasses import dataclass
from typing import *

from marshmallow import post_load
import networkx as nx

import nengo_3d_schemas
from nengo_3d_schemas import Message, Observe, SimulationSteps, Simulation

# nengo_3d_schemas.Observe
class NetworkSchema(nengo_3d_schemas.NetworkSchema):
    @post_load
    def make_user(self, data, **kwargs) -> nx.DiGraph:
        g = nx.DiGraph()
        for node_name, attributes in data['nodes'].items():
            g.add_node(node_name)
        for conn_name, attributes in data['connections'].items():
            g.add_edge(attributes['pre'], attributes['post'])
        return g
