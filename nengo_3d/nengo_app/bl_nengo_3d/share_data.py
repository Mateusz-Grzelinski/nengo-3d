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
import socket
from collections import defaultdict
from datetime import datetime
from typing import *
from uuid import uuid4

import logging
import bpy

from bl_nengo_3d.charts import Axes

logger = logging.getLogger(__name__)


# def update_chart(obj: bpy.types.Object, X, Y, tag=None):
#     ax = share_data.charts[obj.name]
#     ax


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
        self.model: dict[str, bpy.types.Object] = {}
        """Cached model, key=unique name, object=blender object representation"""
        self.charts: dict[str, list[Axes]] = defaultdict(list)
        """
        Cached chart 
        
        dict[key=name element of model (source of data), 
             value=dict[tag (parameter name), plotting object]
        ]
        """

    def register_chart(self, obj: bpy.types.Object, ax: Axes):
        self.charts[obj.name].append(ax)


share_data = _ShareData()  # Instance storing addon state, is used by most of the sub-modules.
