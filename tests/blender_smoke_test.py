"""Headless smoke coverage for GLTF Quick Export."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import bmesh
import bpy


ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = Path("/tmp/blender_gltf_quick_export_smoke")

sys.dont_write_bytecode = True

PACKAGE_NAME = "gltf_quick_export"
if PACKAGE_NAME not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = module
    spec.loader.exec_module(module)

quick_export = sys.modules[PACKAGE_NAME]
from gltf_quick_export.services import run_auto_export_now  # noqa: E402


def snapshot_repo(root: Path) -> dict[Path, tuple[int, int]]:
    snapshot: dict[Path, tuple[int, int]] = {}
    for path in root.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            stat = path.stat()
            snapshot[path.relative_to(root)] = (stat.st_size, stat.st_mtime_ns)
    return snapshot


def clear_scene(scene: bpy.types.Scene) -> None:
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(scene.collection.children):
        scene.collection.children.unlink(collection)
        if collection.users == 0:
            bpy.data.collections.remove(collection)
    for collection in list(bpy.data.collections):
        if collection.users == 0:
            bpy.data.collections.remove(collection)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def create_cube_object(scene: bpy.types.Scene, name: str, location: tuple[float, float, float]) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    scene.collection.objects.link(obj)
    return obj


def select_objects(*objects: bpy.types.Object) -> None:
    for obj in list(bpy.context.selected_objects):
        obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0] if objects else None


def run_manual_export_smoke(scene: bpy.types.Scene) -> None:
    clear_scene(scene)
    if EXPORT_DIR.exists():
        shutil.rmtree(EXPORT_DIR)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    cube = create_cube_object(scene, "ManualExport", (0.0, 0.0, 0.0))
    select_objects(cube)

    scene.quick_export.export.output_filepath = str(EXPORT_DIR / "manual_export.glb")
    scene.quick_export.export.export_scope = "SELECTED"

    result = bpy.ops.quick_export.export_now()
    assert result == {"FINISHED"}, result
    assert (EXPORT_DIR / "manual_export.glb").exists()
    assert scene.quick_export.last_export_summary.endswith(str(EXPORT_DIR / "manual_export.glb"))


def run_edit_mode_export_smoke(scene: bpy.types.Scene) -> None:
    clear_scene(scene)
    if EXPORT_DIR.exists():
        shutil.rmtree(EXPORT_DIR)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    cube = create_cube_object(scene, "EditExport", (0.0, 0.0, 0.0))
    select_objects(cube)

    scene.quick_export.export.output_filepath = str(EXPORT_DIR / "edit_export.glb")
    scene.quick_export.export.export_scope = "SELECTED"

    result = bpy.ops.object.mode_set(mode="EDIT")
    assert result == {"FINISHED"}, result
    edit_mesh = bmesh.from_edit_mesh(cube.data)
    edit_mesh.verts.ensure_lookup_table()
    original_x = cube.data.vertices[0].co.x
    edit_mesh.verts[0].co.x += 1.5
    assert cube.data.vertices[0].co.x == original_x

    result = bpy.ops.quick_export.export_now()
    assert result == {"FINISHED"}, result
    assert cube.mode == "EDIT", cube.mode
    assert bpy.context.view_layer.objects.active == cube
    assert cube.data.vertices[0].co.x != original_x
    assert (EXPORT_DIR / "edit_export.glb").exists()


def run_auto_export_smoke(scene: bpy.types.Scene) -> None:
    clear_scene(scene)
    if EXPORT_DIR.exists():
        shutil.rmtree(EXPORT_DIR)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    cube = create_cube_object(scene, "AutoExport", (0.0, 0.0, 0.0))
    select_objects(cube)

    scene.quick_export.export.output_filepath = str(EXPORT_DIR / "auto_export.glb")
    scene.quick_export.export.export_scope = "SCENE"

    filepath = run_auto_export_now(bpy.context, scene=scene)
    assert filepath == str(EXPORT_DIR / "auto_export.glb")
    assert (EXPORT_DIR / "auto_export.glb").exists()
    assert scene.quick_export.last_export_summary.startswith("Auto-exported GLB to ")


def main() -> None:
    before = snapshot_repo(ROOT)
    quick_export.register()
    try:
        scene = bpy.context.scene
        run_manual_export_smoke(scene)
        run_edit_mode_export_smoke(scene)
        run_auto_export_smoke(scene)
    finally:
        quick_export.unregister()
    after = snapshot_repo(ROOT)
    assert before == after, "Repo contents changed during the smoke test."
    print("GLTF_QUICK_EXPORT_SMOKE_TEST_OK")


if __name__ == "__main__":
    main()
