"""Import Art/Characters/BreadLoaf/SM_BreadLoaf.glb into /Game/Characters/BreadLoaf."""
import os
import unreal

SRC = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "Art", "Characters", "BreadLoaf", "SM_BreadLoaf.glb")
).replace("\\", "/")
DEST = "/Game/Characters/BreadLoaf"
ASSET = "SM_BreadLoaf"


def log(msg):
    unreal.log(f"[BreadLoaf] {msg}")


def main():
    log(f"source={SRC}")
    if not os.path.isfile(SRC):
        log(f"MISSING {SRC}")
        return
    unreal.EditorAssetLibrary.make_directory(DEST)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", SRC)
    task.set_editor_property("destination_path", DEST)
    task.set_editor_property("destination_name", ASSET)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", True)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = list(getattr(task, "imported_object_paths", []) or [])
    log(f"imported_object_paths={paths}")
    found = None
    pkg = f"{DEST}/{ASSET}"
    mesh = unreal.EditorAssetLibrary.load_asset(pkg)
    if not mesh:
        for p in unreal.EditorAssetLibrary.list_assets(DEST, recursive=True, include_folder=False):
            clean = p.split(".")[0]
            asset = unreal.EditorAssetLibrary.load_asset(clean)
            if isinstance(asset, unreal.StaticMesh):
                mesh, pkg = asset, clean
                break
    if not mesh:
        log("no static mesh")
        return
    try:
        ns = mesh.get_editor_property("nanite_settings")
        ns.enabled = True
        mesh.set_editor_property("nanite_settings", ns)
        log("Nanite enabled")
    except Exception as e:
        log(f"Nanite skip: {e}")
    try:
        b = mesh.get_bounds()
        log(f"bounds extent=({b.box_extent.x:.1f},{b.box_extent.y:.1f},{b.box_extent.z:.1f})")
    except Exception as e:
        log(f"bounds skip: {e}")
    unreal.EditorAssetLibrary.save_asset(pkg, only_if_is_dirty=False)
    log(f"saved {pkg}")
    log("done")


if __name__ == "__main__":
    main()
