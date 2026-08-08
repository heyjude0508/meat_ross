import os
import unreal

DEST_PATH = "/Game/SubwayTrain/UI_Blueprint"
ART_DIR = "E:/game/design/Epic Games/project/meat_ross/Art/UI"
VERIFY_DIR = "E:/game/design/Epic Games/project/meat_ross/Saved/TexWhite"

# (asset name, source png)
JOBS = [
    ("A", "A_white.png"),
    ("B", "B_white.png"),
]

# Match the settings the original assets used.
TEX_SETTINGS = {
    "compression_settings": unreal.TextureCompressionSettings.TC_EDITOR_ICON,
    "srgb": True,
    "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS,
    "lod_group": unreal.TextureGroup.TEXTUREGROUP_WORLD,
}


def log(m):
    unreal.log(f"[WhiteTex] {m}")


def import_one(name, png):
    src = os.path.join(ART_DIR, png).replace("\\", "/")
    if not os.path.isfile(src):
        log(f"SOURCE MISSING {src}")
        return False

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", src)
    task.set_editor_property("destination_path", DEST_PATH)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    pkg = f"{DEST_PATH}/{name}"
    tex = unreal.EditorAssetLibrary.load_asset(pkg)
    if not tex:
        log(f"FAILED to load {pkg} after import")
        return False

    for prop, val in TEX_SETTINGS.items():
        try:
            tex.set_editor_property(prop, val)
        except Exception as e:
            log(f"  set {prop} failed: {e}")

    unreal.EditorAssetLibrary.save_asset(pkg, only_if_is_dirty=False)
    log(f"imported {src} -> {pkg}")
    log(f"  size=({tex.blueprint_get_size_x()},{tex.blueprint_get_size_y()}) "
        f"compression={tex.get_editor_property('compression_settings')} "
        f"srgb={tex.get_editor_property('srgb')}")
    return True


def reexport_for_verify(name):
    pkg = f"{DEST_PATH}/{name}"
    tex = unreal.EditorAssetLibrary.load_asset(pkg)
    if not tex:
        return
    os.makedirs(VERIFY_DIR, exist_ok=True)
    out = os.path.join(VERIFY_DIR, f"{name}_verify.png").replace("\\", "/")
    task = unreal.AssetExportTask()
    task.set_editor_property("object", tex)
    task.set_editor_property("filename", out)
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", True)
    task.set_editor_property("exporter", unreal.TextureExporterPNG())
    unreal.Exporter.run_asset_export_task(task)
    log(f"verify export -> {out} exists={os.path.isfile(out)}")


def main():
    for name, png in JOBS:
        if import_one(name, png):
            reexport_for_verify(name)
    log("done")


if __name__ == "__main__":
    main()
