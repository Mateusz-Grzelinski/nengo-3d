# adapted from https://github.com/JacquesLucke/blender_vscode/blob/master/pythonFiles/include/blender_vscode/operators/addon_update.py

import bpy
import sys
import traceback
from bpy.props import *

from bl_nengo_3d.connection_handler import handle_data
from bl_nengo_3d.share_data import share_data


class UpdateAddonOperator(bpy.types.Operator):
    bl_idname = "nengo.update_addon"
    bl_label = "Update Addon"

    module_name: StringProperty(default='bl_nengo_3d')

    def execute(self, context):
        if share_data.client:
            bpy.app.timers.unregister(handle_data)
            share_data.client.close()
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
    bpy.utils.register_class(UpdateAddonOperator)
