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


try:
    OK = True
    from bl_nengo_3d import bl_operators
    from bl_nengo_3d import bl_panels
    from bl_nengo_3d import debug
    from bl_nengo_3d import bl_properties
    from bl_nengo_3d import bl_plot_operators
except ModuleNotFoundError as e:
    logging.error(f'Addon nengo3d did not start: {e}')
    OK = False


def register():
    if not OK:
        return
    bl_plot_operators.register()
    bl_operators.register()
    bl_panels.register()
    bl_properties.register()
    debug.register()
    # charts.register()


def unregister():
    if not OK:
        return
    bl_plot_operators.unregister()
    bl_operators.unregister()
    bl_panels.unregister()
    bl_properties.unregister()
    debug.unregister()
    # charts.unregister()
