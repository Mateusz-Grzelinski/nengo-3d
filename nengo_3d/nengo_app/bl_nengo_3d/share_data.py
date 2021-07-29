# GPLv3 License
#
# Copyright (C) 2020 Ubisoft
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
This module defines global state of the addon. It is encapsulated in a ShareData instance.
"""
import logging
import socket
import struct
from collections import defaultdict
from typing import *

import bpy
import networkx as nx

from bl_nengo_3d.charts import Axes


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
        self.charts: dict[str, dict[str, list[Axes]]] = defaultdict(dict)
        """
        Cached chart 
        
        dict[key=name element of model (source of data), 
             value=dict[tag (parameter name), plotting object]
        ]
        """
        self.simulation_cache = {}
        """
        dict[object, dict[param, list[data]] ]
        """
        self.charts_sources = {}
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
            any_object = next(iter(self.simulation_cache.values()))
            if any_object:
                any_params_data = next(iter(any_object.values()))
                return len(any_params_data)
            return 0
        return None

    def model_get_edge_by_name(self, name):
        for _source, _end, e_attr in self.model_graph.edges.data():
            if e_attr['name'] == name:
                return _source, _end, e_attr
        return None, None, None

    def register_chart(self, source: bpy.types.Object, ax: Axes, data_indices: tuple):
        if not self.charts[source.name].get(ax.parameter):
            self.charts[source.name][ax.parameter] = []
        self.charts[source.name][ax.parameter].append(ax)
        self.charts_sources[ax] = data_indices


share_data = _ShareData()  # Instance storing addon state, is used by most of the sub-modules.
