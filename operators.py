"""Operators for GLTF Quick Export."""

from __future__ import annotations

import bpy
from bpy.types import Operator

from .services import run_manual_export_now


class QUICKEXPORT_OT_export_now(Operator):
    bl_idname = "quick_export.export_now"
    bl_label = "Export Now"
    bl_description = "Export the current selection or scene to the configured GLB file"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.scene is not None and hasattr(context.scene, "quick_export")

    def execute(self, context: bpy.types.Context) -> set[str]:
        try:
            filepath = run_manual_export_now(context)
        except RuntimeError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        self.report({"INFO"}, f"Exported GLB to {filepath}")
        return {"FINISHED"}
