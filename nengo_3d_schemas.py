# from dataclasses import dataclass, field
# import socket
# from enum import Enum
# from pprint import pprint
import sys
from typing import *

from marshmallow import Schema, fields, pre_load, pre_dump


class Request(Schema):
    uri = fields.Str()


class Answer(Schema):
    schema = fields.Str()
    data = fields.Field()
    """Based on schema decode the data field. Data can be any Schema"""

#     def get_data(self, obj):
#         return
#
# s = Answer()
# l = s.load({'schema': Request.__name__, 'data':{'uris': '1'}})
# print(s.dumps(l))


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
