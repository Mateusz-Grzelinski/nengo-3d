import bpy
import numpy as np

debug_axes: 'Axes' = []


class DebugRasterPlotOperator(bpy.types.Operator):
    """Create test chart"""

    bl_idname = 'nengo_3d.debug_raster_plot'
    bl_label = 'Create raster chart'
    bl_options = {'REGISTER'}

    dim: bpy.props.IntProperty(name='Dimenson', min=2, max=3)

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        from bl_nengo_3d.axes import Axes
        t = np.arange(0.0, 2.0, 0.01)
        s = 1 + np.sin(2 * np.pi * t)
        ax = Axes(context=context)
        ax.xlabel('x')
        ax.ylabel('y')
        ax.title(f'Test chart {self.dim}d')
        if self.dim == 3:
            ax.zlabel('z')
            ax.plot(t, s, s, label='1')
        else:
            ax.plot(t, s, label='2')
            ax.plot(t, [-i for i in s], label='3')
        # ax.grid()
        global debug_axes
        debug_axes.append(ax)
        return {'FINISHED'}


class DebugPlotLine(bpy.types.Operator):
    """Create test chart"""

    bl_idname = 'nengo_3d.debug_plot_line'
    bl_label = 'Create chart'
    bl_options = {'REGISTER'}

    dim: bpy.props.IntProperty(name='Dimension', min=2, max=3)

    def execute(self, context):
        from bl_nengo_3d.axes import Axes
        t = np.arange(0.0, 2.0, 0.01)
        s = 1 + np.sin(2 * np.pi * t)
        # ax = Axes(context=context)
        # ax.xlabel('x')
        # ax.ylabel('y')
        # ax.title(f'Test chart {self.dim}d')
        # if self.dim == 3:
        #     ax.zlabel('z')
        #     ax.plot(t, s, s, label='test')
        # else:
        #     ax.plot(t, s, label='test1')
        #     ax.plot(t, [-i for i in s], label='test2')
        # # ax.grid()
        # global debug_axes
        # debug_axes.append(ax)
        return {'FINISHED'}

    # box, bar, barh, pie, hist, hist2d (heat map), scatter, axhline, axvline, table, polar, log

iterator = 0


class DebugUpdatePlotLineOperator(bpy.types.Operator):
    """Create test chart"""

    bl_idname = 'nengo_3d.debug_update_plot_line'
    bl_label = 'Update chart'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return debug_axes

    def execute(self, context):
        global debug_axes, iterator
        start_x = 0.0 + 0.01 * iterator
        end_x = 2.0 + 0.01 * iterator
        t = np.arange(start_x, end_x, 0.01)
        iterator += 5
        s = 1 + np.sin(2 * np.pi * t)
        for ax in debug_axes:
            for line in ax._plot_lines:
                if line.dim == 2:
                    line.set_data(t, s)
                else:
                    line.set_data(t, s, s)
            ax.draw()

        context.area.tag_redraw()
        return {'FINISHED'}

    # box, bar, barh, pie, hist, hist2d (heat map), scatter, axhline, axvline, table, polar, log

# classes = (
#     CreateChartOperator, UpdateChartOperator
# )
