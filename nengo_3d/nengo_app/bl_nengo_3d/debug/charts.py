import bpy

debug_axes: 'Axes' = []


class CreateChartOperator(bpy.types.Operator):
    """Create test chart"""

    bl_idname = 'nengo_3d.chart'
    bl_label = 'Create chart'
    bl_options = {'REGISTER'}

    dim: bpy.props.IntProperty(name='Dimenson', min=2, max=3)

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
        ax.title(f'Test chart {self.dim}d')
        if self.dim == 3:
            ax.zlabel('z')
            ax.plot(t, s, s)
        else:
            ax.plot(t, s)
        # ax.grid()
        global debug_axes
        debug_axes.append(ax)
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
        return debug_axes

    def execute(self, context):
        import numpy as np
        global iterator, debug_axes
        start_x = 0.0 + 0.01 * iterator
        end_x = 2.0 + 0.01 * iterator
        t = np.arange(start_x, end_x, 0.01)
        iterator += 5
        s = 1 + np.sin(2 * np.pi * t)
        # from bl_nengo_3d.charts import Axes
        # debug_axes: Axes
        for ax in debug_axes:
            if ax.dim == 2:
                ax.plot(t, s)
            else:
                ax.plot(t, s, s)
        # debug_axes.draw_x_ticks([str(range(i, 1)) for i in np.linspace(start_x, end_x, num=10)])

        context.area.tag_redraw()
        return {'FINISHED'}

    # box, bar, barh, pie, hist, hist2d (heat map), scatter, axhline, axvline, table, polar, log

# classes = (
#     CreateChartOperator, UpdateChartOperator
# )
