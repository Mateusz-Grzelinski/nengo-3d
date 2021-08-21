import logging

import nengo_3d_schemas
from marshmallow import post_load, pre_dump
from nengo_3d_schemas import Message, Observe, SimulationSteps, Simulation


class PlotLines(nengo_3d_schemas.PlotLines):
    @pre_dump
    def process_axes(self, data: 'Axes', **kwargs):
        ax = data
        node = self.context['node']
        access_path = self.context['access_path']
        return {
            'plot_id': ax.root.name,
            'source': node.name,
            'access_path': access_path,
            'x': [], 'y': []
        }


class NetworkSchema(nengo_3d_schemas.NetworkSchema):
    @post_load
    def make_user(self, data: dict, **kwargs) -> 'bl_nengo_3d.digraph_model.DiGraphModel':
        from bl_nengo_3d.digraph_model import DiGraphModel
        g = DiGraphModel(name=data['name'], networks={}, type=data['type'], class_type=data['class_type'],
                         n_neurons=data['n_neurons'], parent_network=str(data['parent_network']))

        nodes = data.pop('nodes')
        for node_name, attributes in nodes.items():
            # logging.debug(f'Loading node/ensemble: {node_name}, {attributes}')
            g.add_node(node_name)
            for attr_name, attr in attributes.items():
                g.nodes[node_name][attr_name] = attr

        networks = data.pop('networks')
        s = NetworkSchema()
        for net_name, attributes in networks.items():
            # logging.debug(f'Loading subnet: {g.name}: {net_name}, {attributes}')
            _g, _data = s.load(attributes)
            g.graph['networks'][net_name] = _g
            # todo this makes all nodes flat, it is wastefull but easier to implement
            for node, attr in _g.nodes(data=True):
                attr['network'] = net_name
                g.add_node(node, **attr)

        connections = data.pop('connections')
        for conn_name, attributes in connections.items():
            # logging.debug((g, conn_name))
            # assert g.nodes.get(attributes['pre']) is not None, attributes['pre']
            # assert g.nodes.get(attributes['post']) is not None, attributes['post']
            if g.nodes.get(attributes['post']) is None or g.nodes.get(attributes['pre']) is None:
                logging.warning(f'Unknown node: {attributes["post"]}')
            g.add_edge(attributes['pre'], attributes['post'])
            for attr_name, attr in attributes.items():
                g.edges[attributes['pre'], attributes['post']][attr_name] = attr
        return g, data
