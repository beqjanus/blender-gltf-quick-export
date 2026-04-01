"""Export and auto-export services for GLTF Quick Export."""

from __future__ import annotations

import os
import time
import traceback
from contextlib import contextmanager

import bpy
from bpy.app.handlers import persistent

_AUTO_EXPORT_CHECK_INTERVAL = 1.0
_AUTO_EXPORT_NEXT_RUN_BY_SCENE: dict[int, float] = {}
_AUTO_EXPORT_RUNNING = False


def iter_scenes() -> tuple[bpy.types.Scene, ...]:
    scenes = getattr(bpy.data, "scenes", None)
    if scenes is None:
        return ()
    return tuple(scenes)


def scene_mesh_objects(
    context: bpy.types.Context,
    scene: bpy.types.Scene,
) -> list[bpy.types.Object]:
    export_options = scene.quick_export.export
    if export_options.export_scope == "SCENE":
        return [obj for obj in scene.objects if obj.type == "MESH"]
    return [obj for obj in context.selected_objects if obj.type == "MESH"]


def normalized_output_filepath(filepath: str) -> str:
    resolved = bpy.path.abspath(filepath).strip()
    if not resolved:
        raise RuntimeError("Choose an output file before exporting.")

    root, ext = os.path.splitext(resolved)
    if ext.lower() != ".glb":
        resolved = f"{root or resolved}.glb"
    directory = os.path.dirname(resolved)
    if directory:
        os.makedirs(directory, exist_ok=True)
    return resolved


def sync_meshes_from_edit_mode(objects: list[bpy.types.Object]) -> None:
    seen: set[str] = set()
    for obj in objects:
        if obj.type != "MESH":
            continue
        object_key = str(obj.as_pointer())
        if object_key in seen:
            continue
        seen.add(object_key)
        if getattr(obj, "mode", "OBJECT") == "EDIT":
            obj.update_from_editmode()
            if obj.data is not None:
                obj.data.update()


@contextmanager
def temporary_object_mode_for_export(
    context: bpy.types.Context,
    objects: list[bpy.types.Object],
):
    scene = context.scene
    view_layer = context.view_layer
    sync_meshes_from_edit_mode(objects)

    original_active = view_layer.objects.active
    original_mode = getattr(original_active, "mode", "OBJECT") if original_active is not None else "OBJECT"
    switched_mode = False

    if original_active is not None and original_mode != "OBJECT" and bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode="OBJECT")
        switched_mode = True

    try:
        yield
    finally:
        if (
            switched_mode
            and original_active is not None
            and original_active.name in scene.objects
            and bpy.ops.object.mode_set.poll()
        ):
            view_layer.objects.active = original_active
            if not original_active.select_get():
                original_active.select_set(True)
            bpy.ops.object.mode_set(mode=original_mode)


@contextmanager
def temporary_export_selection(
    context: bpy.types.Context,
    source_objects: list[bpy.types.Object],
):
    scene = context.scene
    view_layer = context.view_layer
    original_selection = list(context.selected_objects)
    original_active = view_layer.objects.active

    temp_collection = bpy.data.collections.new("Quick Export Temp")
    scene.collection.children.link(temp_collection)

    duplicates: list[bpy.types.Object] = []
    created_meshes: list[bpy.types.ID] = []
    try:
        for obj in source_objects:
            duplicate = obj.copy()
            if obj.data is not None:
                duplicate.data = obj.data.copy()
                created_meshes.append(duplicate.data)
            duplicate.animation_data_clear()
            duplicate.hide_set(False)
            duplicate.hide_viewport = False
            temp_collection.objects.link(duplicate)
            duplicates.append(duplicate)

        for obj in original_selection:
            obj.select_set(False)
        for duplicate in duplicates:
            duplicate.select_set(True)
        if duplicates:
            view_layer.objects.active = duplicates[0]
        yield
    finally:
        for duplicate in duplicates:
            duplicate.select_set(False)
            bpy.data.objects.remove(duplicate, do_unlink=True)
        for mesh in created_meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        scene.collection.children.unlink(temp_collection)
        bpy.data.collections.remove(temp_collection)

        for obj in original_selection:
            if obj.name in scene.objects:
                obj.select_set(True)
        view_layer.objects.active = original_active


def export_glb(
    context: bpy.types.Context,
    *,
    scene: bpy.types.Scene | None = None,
) -> str:
    scene = scene or context.scene
    export_options = scene.quick_export.export
    filepath = normalized_output_filepath(export_options.output_filepath)
    source_objects = scene_mesh_objects(context, scene)
    if not source_objects:
        if export_options.export_scope == "SCENE":
            raise RuntimeError("No mesh objects are available in the active scene.")
        raise RuntimeError("Select at least one mesh object to export.")

    with temporary_object_mode_for_export(context, source_objects):
        with temporary_export_selection(context, source_objects):
            bpy.ops.export_scene.gltf(
                filepath=filepath,
                export_format="GLB",
                use_selection=True,
                export_apply=export_options.apply_modifiers,
                use_active_scene=True,
                check_existing=False,
            )
    return filepath


def run_manual_export_now(
    context: bpy.types.Context,
    *,
    scene: bpy.types.Scene | None = None,
) -> str:
    scene = scene or context.scene
    filepath = export_glb(context, scene=scene)
    scene.quick_export.last_export_summary = f"Exported GLB to {filepath}"
    return filepath


def auto_export_scene_enabled(scene: bpy.types.Scene | None) -> bool:
    if scene is None or not hasattr(scene, "quick_export") or scene.quick_export is None:
        return False
    export_options = getattr(scene.quick_export, "export", None)
    return bool(export_options is not None and export_options.auto_export_enabled)


def any_auto_export_scene_enabled() -> bool:
    return any(auto_export_scene_enabled(scene) for scene in iter_scenes())


def auto_export_interval_seconds(scene: bpy.types.Scene) -> float:
    return max(1.0, float(scene.quick_export.export.auto_export_interval_seconds))


def _scene_auto_export_key(scene: bpy.types.Scene) -> int:
    return int(scene.as_pointer())


def _schedule_next_auto_export(scene: bpy.types.Scene, *, delay: float | None = None) -> None:
    if not auto_export_scene_enabled(scene):
        _AUTO_EXPORT_NEXT_RUN_BY_SCENE.pop(_scene_auto_export_key(scene), None)
        return
    run_after = auto_export_interval_seconds(scene) if delay is None else max(0.0, delay)
    _AUTO_EXPORT_NEXT_RUN_BY_SCENE[_scene_auto_export_key(scene)] = time.monotonic() + run_after


def _clear_stale_auto_export_schedules() -> None:
    valid_keys = {_scene_auto_export_key(scene) for scene in iter_scenes()}
    for key in list(_AUTO_EXPORT_NEXT_RUN_BY_SCENE):
        if key not in valid_keys:
            _AUTO_EXPORT_NEXT_RUN_BY_SCENE.pop(key, None)


def run_auto_export_now(
    context: bpy.types.Context,
    *,
    scene: bpy.types.Scene | None = None,
) -> str:
    scene = scene or context.scene
    filepath = export_glb(context, scene=scene)
    scene.quick_export.last_export_summary = f"Auto-exported GLB to {filepath} at {time.strftime('%H:%M:%S')}"
    return filepath


def notify_auto_export_settings_changed(scene: bpy.types.Scene | None) -> None:
    if bpy.app.background or scene is None:
        return

    _clear_stale_auto_export_schedules()
    if auto_export_scene_enabled(scene):
        _schedule_next_auto_export(scene)
        _ensure_auto_export_timer()
        return

    _AUTO_EXPORT_NEXT_RUN_BY_SCENE.pop(_scene_auto_export_key(scene), None)
    if not any_auto_export_scene_enabled() and bpy.app.timers.is_registered(_auto_export_timer):
        bpy.app.timers.unregister(_auto_export_timer)


def _next_due_auto_export_delay() -> float:
    if not _AUTO_EXPORT_NEXT_RUN_BY_SCENE:
        return _AUTO_EXPORT_CHECK_INTERVAL
    now = time.monotonic()
    soonest = min(_AUTO_EXPORT_NEXT_RUN_BY_SCENE.values())
    return max(0.1, min(_AUTO_EXPORT_CHECK_INTERVAL, soonest - now))


def _auto_export_timer() -> float | None:
    global _AUTO_EXPORT_RUNNING

    if bpy.app.background:
        return None

    _clear_stale_auto_export_schedules()
    if not any_auto_export_scene_enabled():
        _AUTO_EXPORT_NEXT_RUN_BY_SCENE.clear()
        return None

    context = bpy.context
    scene = getattr(context, "scene", None)
    if scene is None or not auto_export_scene_enabled(scene):
        return _AUTO_EXPORT_CHECK_INTERVAL

    scene_key = _scene_auto_export_key(scene)
    due_at = _AUTO_EXPORT_NEXT_RUN_BY_SCENE.get(scene_key)
    if due_at is None:
        _schedule_next_auto_export(scene)
        return _next_due_auto_export_delay()

    now = time.monotonic()
    if now < due_at or _AUTO_EXPORT_RUNNING:
        return _next_due_auto_export_delay()

    _AUTO_EXPORT_RUNNING = True
    try:
        run_auto_export_now(context, scene=scene)
    except RuntimeError as exc:
        scene.quick_export.last_export_summary = f"Auto-export failed: {exc}"
    except Exception as exc:  # pragma: no cover - defensive logging in Blender timer context
        scene.quick_export.last_export_summary = f"Auto-export failed: {exc}"
        traceback.print_exc()
    finally:
        _AUTO_EXPORT_RUNNING = False
        if auto_export_scene_enabled(scene):
            _schedule_next_auto_export(scene)
        else:
            _AUTO_EXPORT_NEXT_RUN_BY_SCENE.pop(scene_key, None)
    return _next_due_auto_export_delay()


def _ensure_auto_export_timer() -> None:
    if bpy.app.background or not any_auto_export_scene_enabled():
        return
    if not bpy.app.timers.is_registered(_auto_export_timer):
        bpy.app.timers.register(_auto_export_timer, first_interval=_AUTO_EXPORT_CHECK_INTERVAL)


@persistent
def load_post_auto_export_handler(_dummy: object) -> None:
    _AUTO_EXPORT_NEXT_RUN_BY_SCENE.clear()
    if any_auto_export_scene_enabled():
        for scene in iter_scenes():
            if auto_export_scene_enabled(scene):
                _schedule_next_auto_export(scene)
        _ensure_auto_export_timer()


def register_auto_export() -> None:
    _AUTO_EXPORT_NEXT_RUN_BY_SCENE.clear()
    if load_post_auto_export_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post_auto_export_handler)
    if any_auto_export_scene_enabled():
        for scene in iter_scenes():
            if auto_export_scene_enabled(scene):
                _schedule_next_auto_export(scene)
        _ensure_auto_export_timer()


def unregister_auto_export() -> None:
    _AUTO_EXPORT_NEXT_RUN_BY_SCENE.clear()
    if bpy.app.timers.is_registered(_auto_export_timer):
        bpy.app.timers.unregister(_auto_export_timer)
    if load_post_auto_export_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_auto_export_handler)
