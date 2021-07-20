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
from datetime import datetime
from typing import *
from uuid import uuid4

import logging
import bpy

logger = logging.getLogger(__name__)


class _ShareData:
    """
    ShareData is the class storing the global state of the addon.
    """

    def __init__(self):
        self.run_id = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.session_id = 0  # For logging and debug
        self.client: Optional[socket.socket] = None
        self.handle_data: Callable = None
        """This is handle for unregistering function. This function is created using functools.partial"""

        # self.local_server_process = None
        # self.selected_objects_names = []
        # self.pending_test_update = False


share_data = _ShareData()  # Instance storing addon state, is used by most of the sub-modules.
