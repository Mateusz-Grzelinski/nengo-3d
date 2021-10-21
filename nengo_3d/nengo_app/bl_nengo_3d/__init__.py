bl_info = {
    "name": "Nengo 3d",
    "author": "Mateusz Grzeliński",
    "description": "Interactive neural network visualization toolkit. Works only in Nengo app template.",
    "version": (0, 0, 2),
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

OK = True


def register():
    global OK
    import os
    import sys
    import bpy

    # double check for dependencies, just to make sure. Should be handled by Nengo app template
    # script_path = os.path.dirname(__file__)

    # the same path as in blender_app_template_check.py
    third_party_modules = os.path.realpath(os.path.join(bpy.utils.resource_path('USER'),
                                                        r'scripts\startup\bl_app_templates_user',
                                                        'nengo_app', 'blender_pip_modules'))
    if not os.path.exists(third_party_modules):
        logging.error(
            f'This addon depends on third party modules. '
            f'Run nengo_3d.GUI to install them automatically to {third_party_modules}')
        return False

    if not any('blender_pip_modules' in path for path in sys.path):  # third_party_modules not in sys.path:  #
        logging.warning('bl_nengo_3d was run outside Nengo app template. Trying to make it work anyway...')
        sys.path.append(third_party_modules)

    try:
        from bl_nengo_3d import bl_properties
        from bl_nengo_3d import bl_operators
        from bl_nengo_3d import bl_panels
        from bl_nengo_3d import debug
        from bl_nengo_3d import bl_plot_operators
        from bl_nengo_3d import bl_depsgraph_handler
        from bl_nengo_3d import schemas  # sanity check
    except ModuleNotFoundError as e:
        logging.error(f'Addon bl_nengo_3d did not start: {e}')
        OK = False
        return False

    if not OK:
        return False
    bl_properties.register()
    bl_plot_operators.register()
    bl_depsgraph_handler.register()
    bl_operators.register()
    bl_panels.register()
    debug.register()


def unregister():
    global OK

    try:
        from bl_nengo_3d import bl_properties
        from bl_nengo_3d import bl_operators
        from bl_nengo_3d import bl_panels
        from bl_nengo_3d import debug
        from bl_nengo_3d import bl_plot_operators
        from bl_nengo_3d import bl_depsgraph_handler
        from bl_nengo_3d import schemas  # sanity check
    except ModuleNotFoundError as e:
        OK = False

    if not OK:
        return False
    bl_plot_operators.unregister()
    bl_operators.unregister()
    bl_panels.unregister()
    bl_depsgraph_handler.unregister()
    bl_properties.unregister()
    debug.unregister()
