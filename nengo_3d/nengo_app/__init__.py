import os
import sys

script_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(script_path, 'blender_pip_modules'))

import logging
import bpy
from bpy.app.handlers import persistent

logging.basicConfig(
    level=logging.DEBUG,
    format=f'%(levelname)s:{__name__}:"%(pathname)s:%(lineno)d":%(message)s'
)

ADDONS = ['bl_nengo_3d']


@persistent
def load_handler_for_preferences(_):
    logging.info('Changing Preference Defaults!')
    from bpy import context

    prefs = context.preferences
    prefs.use_preferences_save = False

    # kc = context.window_manager.keyconfigs["blender"]


@persistent
def load_handler_for_startup(_):
    logging.info('Changing Startup Defaults!')
    for addon in ADDONS:
        bpy.ops.preferences.addon_enable(module=addon)

    # Use smooth faces.
    # for mesh in bpy.data.meshes:
    #     for poly in mesh.polygons:
    #         poly.use_smooth = True

    # Use material preview shading.
    # for screen in bpy.data.screens:
    #     for area in screen.areas:
    #         for space in area.spaces:
    #             if space.type == 'FILE_BROWSER':
    #                 space.params.directory = os.path.dirname(__file__)
    # space.shading.type = 'MATERIAL'
    # space.shading.use_scene_lights = True


def register():
    logging.info('Registering to Change Defaults')

    # print(sorted(sys.modules.keys()))
    def create_link(directory: str, link_path: str) -> None:
        if os.path.exists(link_path):
            os.remove(link_path)

        if sys.platform == 'win32':
            import _winapi
            _winapi.CreateJunction(str(directory), str(link_path))
        else:
            os.symlink(str(directory), str(link_path), target_is_directory=True)

    addons_dir = bpy.utils.user_resource('SCRIPTS', 'addons')
    os.makedirs(addons_dir, exist_ok=True)
    for addon in ADDONS:
        source = os.path.join(script_path, addon)
        assert os.path.exists(source)
        create_link(directory=source, link_path=os.path.join(addons_dir, addon))

    bpy.app.handlers.load_factory_preferences_post.append(load_handler_for_preferences)
    bpy.app.handlers.load_factory_startup_post.append(load_handler_for_startup)


def unregister():
    logging.info("Unregistering to Change Defaults")
    bpy.app.handlers.load_factory_preferences_post.remove(load_handler_for_preferences)
    bpy.app.handlers.load_factory_startup_post.remove(load_handler_for_startup)
