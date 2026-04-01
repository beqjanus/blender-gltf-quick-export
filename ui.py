"""3D View UI for GLTF Quick Export."""

from __future__ import annotations

import bpy
from bpy.types import Panel


class QUICKEXPORT_PT_main(Panel):
    bl_idname = "QUICKEXPORT_PT_main"
    bl_label = "Quick Export"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Quick Export"

    def draw(self, context: bpy.types.Context) -> None:
        scene_state = context.scene.quick_export
        export_state = scene_state.export

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.prop(export_state, "output_filepath")
        layout.prop(export_state, "export_scope")
        layout.prop(export_state, "apply_modifiers")

        auto_box = layout.box()
        auto_box.use_property_split = True
        auto_box.use_property_decorate = False
        auto_box.label(text="Auto-export GLB")
        auto_box.prop(export_state, "auto_export_enabled")
        auto_box.prop(export_state, "auto_export_interval_seconds")
        auto_box.label(text="Overwrites the existing .glb file.")
        auto_box.label(text="Does not save the .blend file.")

        layout.operator("quick_export.export_now", icon="EXPORT")
        layout.label(text=scene_state.last_export_summary)
