"""Blender property groups for GLTF Quick Export."""

from __future__ import annotations

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

from .constants import EXPORT_SCOPE_ITEMS


def _scene_from_owner(
    context: bpy.types.Context | None,
    owner: bpy.types.ID | None = None,
) -> bpy.types.Scene | None:
    scene = getattr(context, "scene", None)
    if scene is not None and hasattr(scene, "quick_export") and scene.quick_export is not None:
        return scene

    users_scene = getattr(owner, "users_scene", None)
    if users_scene:
        scene = users_scene[0]
        if hasattr(scene, "quick_export") and scene.quick_export is not None:
            return scene
    return None


def _update_auto_export_settings(self: PropertyGroup, context: bpy.types.Context | None) -> None:
    scene = _scene_from_owner(context, getattr(self, "id_data", None))
    if scene is None:
        return

    from .services import notify_auto_export_settings_changed

    notify_auto_export_settings_changed(scene)


class QUICKEXPORTExportOptions(PropertyGroup):
    output_filepath: StringProperty(
        name="Output File",
        description="Target GLB file written by manual export and auto-export",
        default="//quick_export.glb",
        subtype="FILE_PATH",
    )
    export_scope: EnumProperty(
        name="Scope",
        items=EXPORT_SCOPE_ITEMS,
        default="SELECTED",
    )
    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers while exporting",
        default=True,
    )
    auto_export_enabled: BoolProperty(
        name="Auto-export GLB",
        description="Periodically export the current scene state to GLB without saving the .blend file",
        default=False,
        update=_update_auto_export_settings,
    )
    auto_export_interval_seconds: FloatProperty(
        name="Every (Seconds)",
        description="How often to auto-export the GLB file",
        default=30.0,
        min=1.0,
        soft_min=1.0,
        subtype="TIME_ABSOLUTE",
        update=_update_auto_export_settings,
    )


class QUICKEXPORTSceneState(PropertyGroup):
    export: PointerProperty(type=QUICKEXPORTExportOptions)
    last_export_summary: StringProperty(
        name="Export Summary",
        default="Nothing exported yet.",
    )
