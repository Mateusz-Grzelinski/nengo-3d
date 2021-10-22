import bpy

from . import addon_reload
from .addon_reload import ReloadAddonOperator
from .bl_panels import NengoDebugPanel, NengoSimulationCachePanel, NengoSimulationChartPanel, NengoSubnetsPanel, \
    NengoNodesPanel, NengoAttributesPanel
from .charts import DebugUpdatePlotLineOperator, DebugPlotLine, DebugRasterPlotOperator
from .connection import DebugConnectionOperator

# this is special case for registering reload functionality
addon_reload.register()

classes = (
    DebugConnectionOperator,
    NengoDebugPanel,
    NengoSimulationCachePanel,
    DebugPlotLine,
    DebugUpdatePlotLineOperator,
    DebugRasterPlotOperator,
    NengoSimulationChartPanel,
    NengoAttributesPanel,
    NengoSubnetsPanel,
    NengoNodesPanel,
)

register, unregister = bpy.utils.register_classes_factory(classes)
