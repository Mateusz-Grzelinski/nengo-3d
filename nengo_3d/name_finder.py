"""
This module is borrowed from nengo_gui
"""
import logging
from typing import Any
import nengo


class NameFinder:
    def __init__(self, terms: dict[str, Any], model: nengo.Network):
        self.base_terms = terms
        self.known_name = {}
        for k, v in terms.items():
            if not k.startswith("_"):
                try:
                    self.known_name[v] = k
                except TypeError:
                    pass
        self.find_names(model)

    def find_names(self, net: nengo.Network) -> None:
        net_name = self.known_name[net]

        base_lists = ["ensembles", "nodes", "connections", "networks"]
        all_lists = [
            "all_ensembles",
            "all_nodes",
            "all_connections",
            "all_networks",
            "all_objects",
            "all_probes",
        ]

        classes = (nengo.Node, nengo.Ensemble, nengo.Network, nengo.Connection)

        for inst_attr in dir(net):
            private = inst_attr.startswith("_")
            in_lists = inst_attr in base_lists + all_lists
            if not private and not in_lists:
                attr = getattr(net, inst_attr)
                if isinstance(attr, list):
                    for i, obj in enumerate(attr):
                        if obj not in self.known_name:
                            n = "%s.%s[%d]" % (net_name, inst_attr, i)
                            self.known_name[obj] = n
                elif isinstance(attr, classes):
                    if attr not in self.known_name:
                        self.known_name[attr] = "%s.%s" % (net_name, inst_attr)

        for obj_type in base_lists:
            for i, obj in enumerate(getattr(net, obj_type)):
                name = self.known_name.get(obj, None)
                if name is None:
                    name = "%s.%s[%d]" % (net_name, obj_type, i)
                    self.known_name[obj] = name

        for n in net.networks:
            self.find_names(n)

    def name(self, obj: nengo.base.NengoObject) -> str:
        if isinstance(obj, nengo.base.ObjView):
            return self.known_name[obj.obj]
        elif isinstance(obj, nengo.ensemble.Neurons):
            return self.known_name[obj.ensemble]
        else:
            return self.known_name[obj]

    def object(self, name: str) -> nengo.base.NengoObject:
        # todo bad...
        for obj, _name in self.known_name.items():
            if name == _name:
                return obj
        logging.error(f'No object is named "{name}"')
