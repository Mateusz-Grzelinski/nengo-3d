import typing
from typing import *
from itertools import chain
import nengo
from marshmallow import pre_dump, types

from nengo_3d.name_finder import NameFinder
import sys

sys.path.append("..")  # Adds higher directory to python modules path.
import nengo_3d_schemas

Answer = nengo_3d_schemas.Answer
Request = nengo_3d_schemas.Request


class ConnectionSchema(nengo_3d_schemas.ConnectionSchema):
    def __init__(self, *, only: typing.Optional[types.StrSequenceOrSet] = None, exclude: types.StrSequenceOrSet = (),
                 many: bool = False, context: typing.Optional[typing.Dict] = None,
                 load_only: types.StrSequenceOrSet = (), dump_only: types.StrSequenceOrSet = (),
                 partial: typing.Union[bool, types.StrSequenceOrSet] = False, unknown: typing.Optional[str] = None,
                 name_finder: NameFinder):
        super().__init__(only=only, exclude=exclude, many=many, context=context, load_only=load_only,
                         dump_only=dump_only, partial=partial, unknown=unknown)
        self.name_finder = name_finder

    @pre_dump
    def process_connection(self, data: nengo.Connection, **kwargs):
        result = {}
        for param in data.params:
            result[param] = getattr(data, param)
        result['pre'] = self.name_finder.name(data.pre)
        result['post'] = self.name_finder.name(data.post)
        return result


class NodeSchema(nengo_3d_schemas.NodeSchema):
    def __init__(self, *, only: typing.Optional[types.StrSequenceOrSet] = None, exclude: types.StrSequenceOrSet = (),
                 many: bool = False, context: typing.Optional[typing.Dict] = None,
                 load_only: types.StrSequenceOrSet = (), dump_only: types.StrSequenceOrSet = (),
                 partial: typing.Union[bool, types.StrSequenceOrSet] = False, unknown: typing.Optional[str] = None,
                 name_finder: NameFinder):
        super().__init__(only=only, exclude=exclude, many=many, context=context, load_only=load_only,
                         dump_only=dump_only, partial=partial, unknown=unknown)
        self.name_finder = name_finder

    @pre_dump
    def process_node(self, data: nengo.Node, **kwargs):
        result = {}
        for param in data.params:
            result[param] = getattr(data, param)
        return result


class NetworkSchema(nengo_3d_schemas.NetworkSchema):
    def __init__(self, *, only: typing.Optional[types.StrSequenceOrSet] = None, exclude: types.StrSequenceOrSet = (),
                 many: bool = False, context: typing.Optional[typing.Dict] = None,
                 load_only: types.StrSequenceOrSet = (), dump_only: types.StrSequenceOrSet = (),
                 partial: typing.Union[bool, types.StrSequenceOrSet] = False, unknown: typing.Optional[str] = None,
                 name_finder: NameFinder):
        super().__init__(only=only, exclude=exclude, many=many, context=context, load_only=load_only,
                         dump_only=dump_only, partial=partial, unknown=unknown)
        self.name_finder = name_finder

    @pre_dump
    def process_network(self, data: nengo.Network, **kwargs):
        """Give name to network"""
        result = {'nodes': {}, 'connections': {}}
        # this is probably should be called automatically
        s = NodeSchema(name_finder=self.name_finder)
        for obj in chain(data.ensembles, data.nodes):
            result['nodes'][self.name_finder.name(obj)] = s.dump(obj)
        s = ConnectionSchema(name_finder=self.name_finder)
        for obj in data.connections:
            result['connections'][self.name_finder.name(obj)] = s.dump(obj)
        return result

# n = nengo.Network()
# n.nodes
# with n:
#     e = nengo.Ensemble(10, 1)
#     c = nengo.Connection(e, e)
# s = NetworkSchema()
# json = s.dumps(n)
# pprint(json)
# n.nodes.
#
# bowie = dict(name="David Bowie")
# album = dict(artist=bowie, title="Hunky Dory")
#
# schema = AlbumSchema()
# result = schema.dump(album)
# pprint(result, indent=2)
