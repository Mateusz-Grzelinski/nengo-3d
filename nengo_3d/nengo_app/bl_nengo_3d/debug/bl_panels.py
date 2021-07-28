import itertools

import bpy

from .addon_reload import ReloadAddonOperator
from .charts import CreateChartOperator, UpdateChartOperator
from .connection import DebugConnectionOperator


def ranges(i):
    for a, b in itertools.groupby(enumerate(i), lambda pair: pair[1] - pair[0]):
        b = list(b)
        yield b[0][1], b[-1][1]


class NengoDebugPanel(bpy.types.Panel):
    bl_label = 'Nengo 3d Debug'
    bl_idname = 'NENGO_PT_debug'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    # @classmethod
    # def poll(cls, context):
    #     return True

    def draw(self, context):
        layout = self.layout.column()
        from bl_nengo_3d.share_data import share_data
        if share_data.simulation_cache:
            layout.label(text=f'Cached steps: {share_data.simulation_cache_steps()}')
        layout.operator(CreateChartOperator.bl_idname)
        layout.operator(UpdateChartOperator.bl_idname)
        layout.operator(ReloadAddonOperator.bl_idname)
        layout.operator(DebugConnectionOperator.bl_idname)
