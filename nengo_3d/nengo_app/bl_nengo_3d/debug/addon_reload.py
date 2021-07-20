# adapted from https://github.com/JacquesLucke/blender_vscode/blob/master/pythonFiles/include/blender_vscode/operators/addon_update.py
import socket

import bpy
import sys
import traceback
from bpy.props import *

from bl_nengo_3d.connection_handler import handle_data
from bl_nengo_3d.share_data import share_data


class ReloadAddonOperator(bpy.types.Operator):
    """Load code changes
    Can fail if new code has errors"""
    bl_idname = "nengo.reload_addon"
    bl_label = "Reload Addon"

    module_name: StringProperty(default='bl_nengo_3d')

    def execute(self, context):
        if share_data.client:
            if share_data.handle_data and bpy.app.timers.is_registered(share_data.handle_data):
                bpy.app.timers.unregister(share_data.handle_data)
                share_data.handle_data = None
            share_data.client.shutdown(socket.SHUT_RDWR)
            share_data.client.close()
            share_data.client = None
        try:
            bpy.ops.preferences.addon_disable(module=self.module_name)
        except Exception as e:
            traceback.print_exc()
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        for name in list(sys.modules.keys()):
            if name.startswith(self.module_name):
                del sys.modules[name]

        try:
            bpy.ops.preferences.addon_enable(module=self.module_name)
        except Exception as e:
            traceback.print_exc()
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        # redraw_all()
        return {'FINISHED'}


def register():
    bpy.utils.register_class(ReloadAddonOperator)

# def unregister():
#     bpy.utils.unregister_class(ReloadAddonOperator)
