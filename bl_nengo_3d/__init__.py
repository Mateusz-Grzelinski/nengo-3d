bl_info = {
    "name": "Nengo 3d",
    "author": "Mateusz Grzeliński",
    "description": "Interactive neural network visualization toolkit",
    "version": (0, 0, 1),
    "blender": (2, 91, 0),
    "location": "View3D > Nengo 3d",
    "warning": "Experimental addon, can break your scenes",
    "category": "3D View"
}

import logging

logging.basicConfig(level=logging.DEBUG)

from bl_nengo_3d import bl_operators
from bl_nengo_3d import bl_panels
from bl_nengo_3d import debug


def register():
    bl_operators.register()
    bl_panels.register()


def unregister():
    bl_operators.unregister()
    bl_panels.unregister()
