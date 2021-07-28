# from dataclasses import dataclass, field
# import socket
# from enum import Enum
# from pprint import pprint
# import sys
# from typing import *

from marshmallow import Schema, fields, pre_load, pre_dump


class Message(Schema):
    schema = fields.Str(required=True)
    data = fields.Field()
    """Based on schema decode the data field. Data can be any Schema"""


class Observe(Schema):
    source = fields.Str(required=True, allow_none=False)
    parameter = fields.Str(required=True)


class SimulationSteps(Schema):
    step = fields.Int(strict=True)
    # dim= fields.Int()
    node_name = fields.Str()
    # parameters= fields.Method(serialize='get_parameters', deserialize='load_parameters')
    parameters = fields.Dict(keys=fields.Str(),
                             values=fields.List(fields.Float))
    """dict[step, dict[parameter name, values]]"""

    def get_multi_dim_array(self, obj):
        return tuple(obj)


class Simulation(Schema):
    action = fields.Str()
    until = fields.Int()
    # parameter: fields.Dict(keys=fields.Str(), values=fields.List)


class ConnectionSchema(Schema):
    name = fields.Str()
    pre = fields.Str()
    post = fields.Str()
    label = fields.Str(allow_none=True)
    probeable = fields.List(fields.Str())
    size_in = fields.Int()
    size_mid = fields.Int()
    size_out = fields.Int()
    seed = fields.Int(allow_none=True)


class NodeSchema(Schema):
    # name = fields.Str()
    type = fields.Str(required=True)
    probeable = fields.List(fields.Str())
    label = fields.Str(allow_none=True)
    size_in = fields.Int()
    size_out = fields.Int()
    seed = fields.Int(allow_none=True)


class NetworkSchema(Schema):
    file = fields.Str()
    nodes = fields.Dict(keys=fields.Str(), values=fields.Nested(NodeSchema()))
    # ensembles = fields.Dict(keys=fields.Str(), values=fields.Nested(NodeSchema()))
    connections = fields.Dict(keys=fields.Str(), values=fields.Nested(ConnectionSchema()))
    n_neurons = fields.Int()
    # networks = fields.Dict(keys=fields.Str(), values=fields.Nested(ConnectionSchema()))
