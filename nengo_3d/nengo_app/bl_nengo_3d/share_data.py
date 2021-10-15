import logging
import socket
import struct
from collections import defaultdict
from typing import *

import bpy
import networkx as nx
import collections

from bl_nengo_3d import colors
from bl_nengo_3d.axes import Axes, Line


class _ShareData:
    """
    ShareData is the class storing the global state of the addon.
    """

    def __init__(self):
        from bl_nengo_3d.digraph_model import GraphModel
        # self.run_id = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        # self.session_id = 0  # For logging and debug
        self.client: Optional[socket.socket] = None
        self.handle_data: Optional[Callable] = None
        """This is handle for unregistering function. This function is created using functools.partial thus 
        
        >>> assert functools.partial(int, base=10) == functools.partial(int, base=10) # false
        
        """

        # caching and small dependency graph
        # self.model: dict[str, bpy.types.Object] = {}
        self.model_graph: Optional[GraphModel] = None
        self.model_graph_view: Optional[nx.MultiDiGraph] = None
        self.charts: dict[str, list[Axes]] = defaultdict(list)
        # self.simulation_cache_step = list()
        self.simulation_cache = defaultdict(list)
        """
        dict[(object, access_path), list[data]] ]
        """
        self.step_when_ready = 0
        """
        Change current frame when received data from server 
        """
        self.resume_playback_on_steps = False
        """buggy... sometimes we need to wait for data during playback. We need to temporarily stop and then resume"""
        self.requested_steps_until = -1
        self.current_step = -1

    def sendall(self, msg: bytes):
        try:
            self.client.sendall(struct.pack("i", len(msg)) + msg)
            return True
        except OSError as e:
            logging.exception(e)
            return False

    def simulation_cache_steps(self):
        if self.simulation_cache:
            cached_steps = max(len(i) for i in self.simulation_cache.values())
            return cached_steps
        return None

    def register_chart(self, ax: Axes):
        axes = self.charts[ax._nengo_axes.model_source]
        if ax not in axes:
            axes.append(ax)

    def get_registered_chart(self, ax_prop: 'AxesProperties'):
        axes = self.charts.get(ax_prop.model_source)
        for ax in axes:
            if ax.root.name == ax_prop.object:
                return ax

    def get_all_sources(self, nengo_3d: 'Nengo3dProperties'):
        from bl_nengo_3d.bl_properties import LineProperties, Nengo3dProperties
        from bl_nengo_3d.bl_properties import LineSourceProperties
        nengo_3d: Nengo3dProperties
        observe = set()
        plot = set()
        if self.model_graph_view and nengo_3d.node_color == 'MODEL_DYNAMIC':
            for node, node_data in self.model_graph_view.nodes(data=True):
                # todo check if node has this path
                observe.add((node, nengo_3d.node_dynamic_access_path))
        if self.model_graph_view and nengo_3d.edge_color == 'MODEL_DYNAMIC':
            for e_source, e_target, key, e_data in self.model_graph_view.edges(data=True, keys=True):
                e_data = self.model_graph.edges[e_data['pre'], e_data['post'], key]
                observe.add((e_data['name'], nengo_3d.edge_dynamic_access_path))
        for source, axes in self.charts.items():
            for ax in axes:
                for line in ax.lines:
                    line: LineProperties
                    line_source: LineSourceProperties = line.source
                    if line_source.iterate_step:
                        observe.add((line_source.source_obj, line_source.access_path))
                    else:
                        plot.add((line_source.source_obj, line_source.access_path, line_source.fixed_step))
        return observe, plot


share_data = _ShareData()  # Instance storing addon state, is used by most of the sub-modules.
