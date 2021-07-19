# from dataclasses import dataclass, field
# import socket
# from enum import Enum
# from pprint import pprint
import sys
from typing import *

from marshmallow import Schema, fields, pre_load, pre_dump


class ConnectionSchema(Schema):
    # name = fields.Str()
    label = fields.Str(allow_none=True)
    pre = fields.Str()
    post = fields.Str()


class NodeSchema(Schema):
    # name = fields.Str()
    label = fields.Str(allow_none=True)


class NetworkSchema(Schema):
    # name = fields.Str()
    nodes = fields.Dict(keys=fields.Str(), values=fields.Nested(NodeSchema()))
    # ensembles = fields.Dict(keys=fields.Str(), values=fields.Nested(NodeSchema()))
    connections = fields.Dict(keys=fields.Str(), values=fields.Nested(ConnectionSchema()))
    # networks = fields.Dict(keys=fields.Str(), values=fields.Nested(ConnectionSchema()))
