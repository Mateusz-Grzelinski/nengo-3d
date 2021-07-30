import bpy

from . import addon_reload
from .addon_reload import ReloadAddonOperator
from .bl_panels import NengoDebugPanel, NengoSimulationCachePanel
from .charts import UpdateChartOperator, CreateChartOperator
from .connection import DebugConnectionOperator

# this is special case for registering reload functionality
addon_reload.register()

classes = (
    DebugConnectionOperator,
    NengoDebugPanel,
    NengoSimulationCachePanel,
    CreateChartOperator,
    UpdateChartOperator
)

register, unregister = bpy.utils.register_classes_factory(classes)
