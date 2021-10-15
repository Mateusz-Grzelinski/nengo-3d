import logging

import nengo_3d_schemas
from marshmallow import post_load, pre_dump

Message = nengo_3d_schemas.Message
Observe = nengo_3d_schemas.Observe
SimulationSteps = nengo_3d_schemas.SimulationSteps
Simulation = nengo_3d_schemas.Simulation
PlotLines = nengo_3d_schemas.PlotLines

# class PlotLines(nengo_3d_schemas.PlotLines):
#     @pre_dump
#     def process_axes(self, data: 'Axes', **kwargs):
#         ax = data
#         source_obj_name = self.context['source_obj_name']
#         access_path = self.context['access_path']
#         step = self.context['step']
#         return {
#             # 'plot_id': ax.root.name,
#             # line_id?
#             'source': source_obj_name,
#             'access_path': access_path,
#             'step': step,
#             'x': [], 'y': []
#         }


class NetworkSchema(nengo_3d_schemas.NetworkSchema):
    @post_load
    def make_user(self, data: dict, **kwargs) -> 'bl_nengo_3d.digraph_model.GraphModel':
        from bl_nengo_3d.digraph_model import GraphModel
        g = GraphModel(
            name=data['network_name'], network_name=data['network_name'], _networks={}, type=data['type'],
            class_type=data['class_type'], n_neurons=data['n_neurons'], parent_network=str(data['parent_network']),
            module=data['module']
        )

        nodes = data['nodes']
        for node_name, attributes in nodes.items():
            # logging.debug(f'Loading node/ensemble: {g}: {node_name}, {attributes}')
            g.add_node(node_name)
            for attr_name, attr in attributes.items():
                g.nodes[node_name][attr_name] = attr

        networks = data['networks']
        s = NetworkSchema()
        for net_name, attributes in networks.items():
            # logging.debug(f'Loading subnet: {g.name}: {net_name}, {attributes}')
            _g, _data = s.load(attributes)
            # logging.debug(f'Subnet {_g}:{_g.nodes(data=True)}')
            # for node, attr in _g.nodes(data=True):
            #     attr['network_name'] = attributes['network_name']
            g.graph['_networks'][net_name] = _g

        connections = data.pop('connections')
        for conn_name, attributes in connections.items():
            # logging.debug((g, conn_name))
            # at this point, all nodes should be known ...
            if g.get_node_or_subnet_data(attributes['post']) is None:
                logging.warning(f'Unknown node: {attributes["post"]}')
            if g.get_node_or_subnet_data(attributes['pre']) is None:
                logging.warning(f'Unknown node: {attributes["pre"]}')
            g.add_edge(attributes['pre'], attributes['post'], key=conn_name)
            for attr_name, attr in attributes.items():
                g.edges[attributes['pre'], attributes['post'], conn_name][attr_name] = attr
            # ... but they are probably nested inside subnets
            node_pre = g.nodes[attributes['pre']]
            if not node_pre:
                node_pre['dummy'] = True
            node_post = g.nodes[attributes['post']]
            if not node_post:
                node_post['dummy'] = True
        # logging.debug(f'{g}:{g.nodes(data=True)}')
        return g, data
