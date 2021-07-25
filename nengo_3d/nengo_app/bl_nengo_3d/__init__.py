import sys

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

logging.basicConfig(
    level=logging.DEBUG,
    format=f'%(levelname)s:{__name__}:"%(pathname)s:%(lineno)d":%(message)s'
)

from bl_nengo_3d import bl_operators
from bl_nengo_3d import bl_panels
from bl_nengo_3d import debug
from bl_nengo_3d import bl_properties
# from bl_nengo_3d import charts
from bl_nengo_3d import bl_context_menu


def register():
    bl_context_menu.register()
    bl_operators.register()
    bl_panels.register()
    bl_properties.register()
    debug.register()
    # charts.register()


def unregister():
    bl_context_menu.unregister()
    bl_operators.unregister()
    bl_panels.unregister()
    bl_properties.unregister()
    debug.unregister()
    # charts.unregister()
