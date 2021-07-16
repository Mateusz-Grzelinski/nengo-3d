from dataclasses import dataclass, field
import socket
from enum import Enum
from pprint import pprint
from typing import *

import nengo
from marshmallow import Schema, fields, pre_load, pre_dump


# class Component:
#     def update_client(self, client: socket.socket):
#         """Send any required information to the client.
#
#         This method is called regularly by Server.ws_viz_component().  You
#         send text data to the client-side via a WebSocket as follows:
#             client.write_text(data)
#         You send binary data as:
#             client.write_binary(data)
#         """
#         pass
#
#     def message(self, msg):
#         """Receive data from the client.
#
#         Any data sent by the client ove the WebSocket will be passed into
#         this method.
#         """
#         print("unhandled message", msg)
#
#     def finish(self):
#         """Close this Component"""
#         pass
#
#     def add_nengo_objects(self, page):
#         """Add or modify the nengo model before build.
#
#         Components may need to modify the underlying nengo.Network by adding
#         Nodes and Connections or modifying the structure in other ways.
#         This method will be called for all Components just before the build
#         phase.
#         """
#         pass
#
#     def remove_nengo_objects(self, page):
#         """Undo the effects of add_nengo_objects.
#
#         After the build is complete, remove the changes to the nengo.Network
#         so that it is all set to be built again in the future.
#         """
#         pass


# @dataclass
# class Network:
#     objects: dict[str, 'NengoObject'] = field(default_factory=dict)
#
#
# @dataclass
# class NengoObject:
#     # uuid: str
#     label: Optional[str]
#     type: str
#     class_name: str
#     params: list[str]
#
#
# @dataclass
# class Node(NengoObject):
#     size_in: int
#     size_out: int


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


