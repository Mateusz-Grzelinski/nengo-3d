import bpy

debug_axes: 'Axes' = None


class CreateChartOperator(bpy.types.Operator):
    """Create test chart"""

    bl_idname = 'nengo_3d.chart'
    bl_label = 'Create chart'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        import numpy as np
        from bl_nengo_3d.charts import Axes
        t = np.arange(0.0, 2.0, 0.01)
        s = 1 + np.sin(2 * np.pi * t)
        ax = Axes(context=context)
        ax.xlabel('x')
        ax.ylabel('y')
        # ax.title = 'Title'
        # ax.grid()
        ax.plot(t, s)
        global debug_axes
        debug_axes = ax
        return {'FINISHED'}

    # box, bar, barh, pie, hist, hist2d (heat map), scatter, axhline, axvline, table, polar, log


iterator = 0


class UpdateChartOperator(bpy.types.Operator):
    """Create test chart"""

    bl_idname = 'nengo_3d.chart_update'
    bl_label = 'Update chart'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return debug_axes is not None

    def execute(self, context):
        import numpy as np
        global iterator, debug_axes
        start_x = 0.0 + 0.01 * iterator
        end_x = 2.0 + 0.01 * iterator
        t = np.arange(start_x, end_x, 0.01)
        iterator += 2
        s = 1 + np.sin(2 * np.pi * t)
        # from bl_nengo_3d.charts import Axes
        # debug_axes: Axes
        debug_axes.plot(t, s)
        # debug_axes.draw_x_ticks([str(range(i, 1)) for i in np.linspace(start_x, end_x, num=10)])

        context.area.tag_redraw()
        return {'FINISHED'}

    # box, bar, barh, pie, hist, hist2d (heat map), scatter, axhline, axvline, table, polar, log

# classes = (
#     CreateChartOperator, UpdateChartOperator
# )
