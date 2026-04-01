"""GLTF Quick Export Blender extension entrypoint."""

from __future__ import annotations

import bpy

from .operators import QUICKEXPORT_OT_export_now
from .services import register_auto_export, unregister_auto_export
from .state import QUICKEXPORTExportOptions, QUICKEXPORTSceneState
from .ui import QUICKEXPORT_PT_main

bl_info = {
    "name": "GLTF Quick Export",
    "author": "Beq Janus",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Quick Export",
    "description": "Standalone GLB export and timed auto-export",
    "category": "Import-Export",
}


CLASSES = (
    QUICKEXPORTExportOptions,
    QUICKEXPORTSceneState,
    QUICKEXPORT_OT_export_now,
    QUICKEXPORT_PT_main,
)


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Scene.quick_export = bpy.props.PointerProperty(type=QUICKEXPORTSceneState)
    register_auto_export()


def unregister() -> None:
    unregister_auto_export()
    del bpy.types.Scene.quick_export

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
