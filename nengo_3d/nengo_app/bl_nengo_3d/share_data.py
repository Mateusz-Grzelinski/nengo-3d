import logging
import socket
import struct
from collections import defaultdict
from typing import *

import bpy
import networkx as nx
import collections

from bl_nengo_3d import colors
from bl_nengo_3d.charts import Axes, Line


class Indices(NamedTuple):
    x: int
    x_is_step: bool
    y: Optional[int]
    y_multi_dim: Optional[str]
    z_is_step: bool
    z: Optional[int]


class _ShareData:
    """
    ShareData is the class storing the global state of the addon.
    """

    def __init__(self):
        from bl_nengo_3d.digraph_model import DiGraphModel
        # self.run_id = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        # self.session_id = 0  # For logging and debug
        self.client: Optional[socket.socket] = None
        self.handle_data: Optional[Callable] = None
        """This is handle for unregistering function. This function is created using functools.partial thus 
        
        >>> assert functools.partial(int, base=10) == functools.partial(int, base=10) # false
        
        """

        # caching and small dependency graph
        # self.model: dict[str, bpy.types.Object] = {}
        self.model_graph: Optional[DiGraphModel] = None
        self.model_graph_view: Optional[DiGraphModel] = None
        self.charts = defaultdict(list)
        """dict[(source, access_path), list[Axes]]"""
        # self.simulation_cache_step = list()
        self.simulation_cache = defaultdict(list)
        """
        dict[(object, access_path), list[data]] ]
        """
        self.plot_line_sources = {}
        """chart/line -> (x,y,z)]
        """
        self.step_when_ready = 0
        """
        Change current frame when received data from server 
        """
        self.resume_playback_on_steps = False
        """buggy... sometimes we need to wait for data during playback. We need to temporarily stop and then resume"""
        self.requested_steps_until = -1
        self.current_step = -1
        self.color_gen = colors.cycle_color((0.65, 0.65, 0.65))

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

    def model_get_edge_by_name(self, name):
        for _source, _end, e_attr in self.model_graph.edges.data():
            if e_attr['name'] == name:
                return _source, _end, e_attr
        return None, None, None

    def get_chart(self, source: str, access_path: str) -> list[Axes]:
        return self.charts[source, access_path]

    def register_chart(self, source: str, access_path: str, ax: Axes):
        # if not self.charts[source.name].get(ax.parameter):
        #     self.charts[source.name][ax.parameter] = []
        charts = self.charts[source, access_path]
        if ax not in charts:
            charts.append(ax)

    def register_plot_line_source(self, line: Line, xindex: int, yindex: int, yindex_multi_dim: str, zindex: int = None,
                                  x_is_step: bool = False, z_is_step: bool = False):
        self.plot_line_sources[line] = Indices(x=xindex, y=yindex, y_multi_dim=yindex_multi_dim, z=zindex,
                                               x_is_step=x_is_step, z_is_step=z_is_step)


share_data = _ShareData()  # Instance storing addon state, is used by most of the sub-modules.
