import logging
from typing import Generator, Optional, Union, AbstractSet, Tuple

import networkx as nx
from bl_nengo_3d.bl_properties import Nengo3dProperties, Nengo3dShowNetwork
from networkx.classes.reportviews import NodeView, OutEdgeView


class DiGraphModel(nx.DiGraph):
    def __init__(self, incoming_graph_data=None, **attr):
        super().__init__(incoming_graph_data, **attr)

    def get_subnetwork_path_by_node(self, node_name: str, _result=None) -> Optional[list['DiGraphModel']]:
        # todo this is misleading in current flat graph
        if not _result:
            _result = [self]

        value = self.nodes.get(node_name)
        if value:
            _result.extend(value)
            return _result
        else:
            for sub_graph in self.networks.values():
                r = sub_graph.nodes.get(node_name)
                if r:
                    _result.extend(sub_graph)
                    return _result
                else:
                    _result.extend(sub_graph.get_subnetwork_path_by_node(node_name, _result=_result))
                    return _result
        return []

    def get_subnetwork_by_node(self, node_name: str) -> Optional['DiGraphModel']:
        # todo this is misleading in current flat graph
        value = self.nodes.get(node_name)
        if value:
            return self
        else:
            val = None
            for sub_graph in self.networks.values():
                val = sub_graph.get_subnetwork_by_node(node_name)
                if val:
                    return sub_graph
        return None

    def list_subnetworks(self) -> Generator['DiGraphModel', None, None]:
        for net in self.networks.values():
            yield net
            yield from net.list_subnetworks()

    def get_node_data_from_subnets(self, node_name: str) -> Optional[dict]:
        """Return node data from any subnetwork. Return None if node does not exist"""
        sub = self.get_subnetwork_by_node(node_name)
        if sub is None:
            return None
        return sub.nodes[node_name]

    def get_subnetwork(self, subnet_name: str) -> 'DiGraphModel':
        """Return subnetwork with name subnet_name from graph"""
        sub = self.networks.get(subnet_name)
        if sub:
            return sub
        else:
            sub = None
            for net in self.networks.values():
                sub = net.get_subnetwork(subnet_name)
                if sub:
                    return sub

    def get_subnetwork_path(self, subnet_name: str, _result=None) -> list['DiGraphModel']:
        """Return list of subnetworks that lead to subnet_name"""
        if _result is None:
            _result = [self]

        sub = self.networks.get(subnet_name)
        if sub:
            _result.append(sub)
            return _result
        else:
            for net in self.networks.values():
                sub = net.get_subnetwork_path(subnet_name, _result=_result)
                logging.debug(sub)
                if sub:
                    _result.append(sub)
                    logging.debug(_result)
                    return _result

    # def get_node_or_subnet(self, key: str) -> Optional[Union['DiGraphModel', dict]]:
    #     subnet = self.get_subnetwork(key)
    #     if subnet:
    #         return subnet
    #     node = self.get_node_data_from_subnets(key)
    #     return node

    def get_node_or_subnet_data(self, key: str) -> Optional[dict]:
        subnet = self.get_subnetwork(key)
        if subnet:
            return subnet.graph
        node = self.get_node_data_from_subnets(key)
        return node

    def get_graph_view(self, nengo_3d: Nengo3dProperties):
        """Get sub graph ready for drawing"""
        g = DiGraphModel()

        for e_src, e_dst, e_data in self.edges(data=True):
            node_src = self.get_node_data_from_subnets(e_src)
            # logging.debug(node_src)
            # net_src = self.get_subnetwork(node_src['network'])
            subnets = self.get_subnetwork_path(node_src['network'])
            edge_view_src = e_src
            for subnet in subnets:
                # logging.debug((subnet, e_src, node_src['network'],
                #                nengo_3d.expand_subnetworks[node_src['network']].expand))
                if not nengo_3d.expand_subnetworks[subnet.name].expand:
                    edge_view_src = subnet.name
                    break

            node_dst = self.get_node_data_from_subnets(e_dst)
            subnets = self.get_subnetwork_path(node_dst['network'])
            edge_view_dst = e_dst
            for subnet in subnets:
                if not nengo_3d.expand_subnetworks[subnet.name].expand:
                    edge_view_dst = subnet.name
                    break

            if edge_view_src == edge_view_dst:
                continue
            g.add_edge(edge_view_src, edge_view_dst, **e_data)

        for node_name, node_data in g.nodes(data=True):
            data_from_subnets = self.get_node_or_subnet_data(node_name)
            node_data.update(data_from_subnets)
        # logging.debug(list(g.nodes(data=True)))
        # logging.debug(list(g.edges(data=True)))
        return g

    @property
    def networks(self) -> dict[str, 'DiGraphModel']:
        return self.graph['networks']

    @property
    def type(self) -> str:
        return self.graph['type']

    @property
    def class_type(self) -> str:
        return self.graph['class_type']

    @property
    def n_neurons(self) -> int:
        return self.graph['n_neurons']

    def __str__(self):
        return f'{type(self).__name__}(name={self.name})'

    def __repr__(self):
        return str(self)


# class NodeViewModel(NodeView):
#     def __init__(self, graph, nengo_3d: Nengo3dProperties = None):
#         super().__init__(graph)
#         self.nengo_3d = nengo_3d
#         # todo regenerate self._nodes
#
#     def __call__(self, data=False, default=None):
#         # todo adjust based on nengo_3d
#         return super().__call__(data, default)
#
#     def __getitem__(self, n):
#         # todo adjust based on nengo_3d
#         return super().__getitem__(n)
#
#
# class OutEdgeViewModel(OutEdgeView):
#     def __init__(self, graph, nengo_3d: Nengo3dProperties = None):
#         super().__init__(graph)
#         self.nengo_3d = nengo_3d
#
#     def __call__(self, nbunch=None, data=False, default=None):
#         # todo adjust based on nengo_3d
#         return super().__call__(nbunch, data, default)
#
#     def __getitem__(self, n):
#         # todo adjust based on nengo_3d
#         return super().__getitem__(n)
#
#
# class DiGraphModelView(DiGraphModel):
#     @property
#     def nodes(self):
#         nodes = NodeViewModel(self)
#         self.__dict__["nodes"] = nodes
#         return nodes
#
#     @property
#     def edges(self):
#         return OutEdgeViewModel(self)
#         # return super().edges()
#
#     def successors(self, n):
#         return super().successors(n)
