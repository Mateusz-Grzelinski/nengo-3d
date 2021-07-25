import bpy

from .charts import CreateChartOperator, UpdateChartOperator
from .addon_reload import ReloadAddonOperator
from .connection import DebugConnectionOperator


class NengoDebugPanel(bpy.types.Panel):
    bl_label = 'Nengo 3d Debug'
    bl_idname = 'NENGO_PT_debug'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout.column()
        layout.operator(CreateChartOperator.bl_idname)
        layout.operator(UpdateChartOperator.bl_idname)
        layout.operator(ReloadAddonOperator.bl_idname)
        layout.operator(DebugConnectionOperator.bl_idname)