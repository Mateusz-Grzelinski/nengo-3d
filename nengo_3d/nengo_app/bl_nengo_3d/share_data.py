import logging
import socket
import struct
from collections import defaultdict
from typing import *

import bpy
import networkx as nx
import collections

from bl_nengo_3d.charts import Axes, Line


class Indices2(NamedTuple):
    x: int
    y: int


class Indices3(NamedTuple):
    x: int
    y: int
    z: int


class _ShareData:
    """
    ShareData is the class storing the global state of the addon.
    """

    def __init__(self):
        # self.run_id = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        # self.session_id = 0  # For logging and debug
        self.client: Optional[socket.socket] = None
        self.handle_data: Optional[Callable] = None
        """This is handle for unregistering function. This function is created using functools.partial thus 
        
        >>> assert functools.partial(int, base=10) == functools.partial(int, base=10) # false
        
        """

        # caching and small dependency graph
        # self.model: dict[str, bpy.types.Object] = {}
        self.model_graph: nx.DiGraph = None
        """Cached model, key=unique name, object=blender object representation"""
        self.charts = defaultdict(list)
        """
        Cached chart 
        """
        self.simulation_cache = defaultdict(list)
        """
        dict[(object, is_neurons, param), list[data]] ]
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

    # def get_simulation_cache(self, object, is_neurons, param):
    #     return self.simulation_cache[object, param, is_neurons]

    def get_chart(self, source: str, is_neurons: bool) -> list[Axes]:
        return self.charts[source, is_neurons]

    def register_chart(self, source: str, is_neurons: bool, ax: Axes):
        # if not self.charts[source.name].get(ax.parameter):
        #     self.charts[source.name][ax.parameter] = []
        charts = self.charts[source, is_neurons]
        if ax not in charts:
            charts.append(ax)

    def register_plot_line_source(self, line: Line, data_indices: tuple):
        if len(data_indices) == 2:
            self.plot_line_sources[line] = Indices2(*data_indices)
        else:
            self.plot_line_sources[line] = Indices3(*data_indices)


share_data = _ShareData()  # Instance storing addon state, is used by most of the sub-modules.
