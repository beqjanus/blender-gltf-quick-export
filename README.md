# GLTF Quick Export

Standalone Blender extension for fast one-file GLB export and timed auto-export.

This repo intentionally does not include [SLender](https://github.com/beqjanus/slender)'s LOD management, asset tracking, validation, or Second Life-specific tooling. It is meant for creators who already have their own scene workflow and just want a repeatable GLB export target that can refresh automatically.

## Features

- Manual `Export Now` button
- GLB-only export
- Exports either:
  - selected mesh objects
  - all mesh objects in the active scene
- Timed auto-export with interval in seconds
- Overwrites the same `.glb` output file each time
- Does not save the `.blend`
- Flushes edit-mode mesh changes before export
- Restores the previous mode after export

## UI

`3D View > Sidebar > Quick Export`

Controls:

- `Output File`
- `Scope`
- `Apply Modifiers`
- `Auto-export GLB`
- `Every (Seconds)`
- `Export Now`

## Install

Build the extension zip:

```bash
blender --command extension build --source-dir /home/me/src/blender-gltf-quick-export --output-dir /tmp/quick-export-dist
```

Then install it in Blender from:

`Edit > Preferences > Extensions > Install from Disk...`

## Development

If you want a fast local loop, symlink the repo into Blender's user extension directory and restart Blender after structural changes.

## Smoke Test

Run the headless smoke suite with:

```bash
blender --background --factory-startup --python /home/me/src/blender-gltf-quick-export/tests/blender_smoke_test.py
```

The smoke test covers:

- manual export
- export from edit mode
- direct auto-export path

## Releases

- `Build Preview Extension` runs on pull requests, pushes to `master`, and manual workflow runs.
- Preview packages are renamed to include `-preview-<sha>`, for example `gltf_quick_export-0.1.0-preview-1a2b3c4.zip`, and are uploaded only as workflow artifacts.
- `Release Extension` runs only when pushing a tag such as `v0.1.0`.
- The release workflow verifies that the tag matches `version` in `blender_manifest.toml` before publishing `gltf_quick_export-0.1.0.zip` to the GitHub release for that tag.
