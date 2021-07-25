import bpy
from bl_nengo_3d.share_data import share_data


class DebugConnectionOperator(bpy.types.Operator):
    """Send custom message via socket
    Response will be processed via `connection_handler.handle_data`"""

    bl_idname = 'nengo_3d.connect_debug'
    bl_label = 'Send debug message'
    bl_options = {'REGISTER'}

    message: bpy.props.StringProperty(
        name="Debug Message",
        description="Send any message via socket",
        default="{\"uri\":\"model\"}"
    )

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "message")

    @classmethod
    def poll(cls, context):
        return share_data.client is not None

    def execute(self, context):
        share_data.client.send(self.message.encode('utf-8'))
        return {'FINISHED'}
