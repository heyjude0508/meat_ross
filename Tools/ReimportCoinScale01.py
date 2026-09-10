"""Reimport the Office Coin GLB at Import Uniform Scale 0.1, then reset level Coin actors to scale 1."""
from __future__ import annotations

import os
import traceback

import unreal

REPORT_PATH = r"E:/game/design/Epic Games/project/meat_ross/Tools/_reimport_coin_report.txt"
MAP_PATH = "/Game/Office/Maps/Office"
MESH_PKG = "/Game/Office/Models/Coin/StaticMeshes/Coin"
DEST_PATH = "/Game/Office/Models/Coin/StaticMeshes"
ASSET_NAME = "Coin"
UNIFORM_SCALE = 0.1

KNOWN_CANDIDATES = [
    r"C:/Users/westl/Downloads/Coin.glb",
    r"C:/Users/westl/Downloads/Coin.gltf",
    r"C:/Users/westl/Desktop/Coin.glb",
    r"E:/game/design/Epic Games/project/meat_ross/Art/Coin.glb",
]

SEARCH_ROOTS = [
    os.path.expanduser(r"~/Downloads"),
    os.path.expanduser(r"~/Desktop"),
    os.path.expanduser(r"~/Documents"),
    r"E:/game/design/Epic Games/project/meat_ross/Art",
    r"E:/game/design/Epic Games/project/meat_ross/Content/Office/Models/Coin",
    r"E:/game/design/Epic Games/project/meat_ross",
    r"C:/Users/westl/Downloads",
    r"C:/Users/westl/Desktop",
    r"C:/Users/westl/Documents",
    r"C:/Users/westl/Documents/WeChat Files",
    os.path.expanduser(r"~/AppData/Local/Temp"),
]

LINES = []


def log(msg):
    line = f"[ReimportCoin] {msg}"
    unreal.log(line)
    print(line)
    LINES.append(str(msg))


def flush_report():
    try:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(LINES) + "\n")
    except Exception as e:
        unreal.log(f"[ReimportCoin] report write failed: {e}")


def safe_get(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def actor_label(actor):
    try:
        return actor.get_actor_label()
    except Exception:
        return actor.get_name()


def mesh_bounds_str(mesh):
    try:
        b = mesh.get_bounds()
        e = b.box_extent
        o = b.origin
        return (
            f"origin=({o.x:.3f},{o.y:.3f},{o.z:.3f}) "
            f"extent=({e.x:.3f},{e.y:.3f},{e.z:.3f})"
        )
    except Exception as e:
        return f"<bounds err {e}>"


def all_level_actors():
    try:
        return list(unreal.EditorLevelLibrary.get_all_level_actors() or [])
    except Exception:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        return list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) or [])


def find_coin_mesh():
    mesh = unreal.EditorAssetLibrary.load_asset(MESH_PKG)
    if isinstance(mesh, unreal.StaticMesh):
        return mesh, MESH_PKG
    # Unsaved / redirected packages
    for folder in (
        "/Game/Office/Models/Coin",
        "/Game/Office/Models",
        "/Game/Office",
    ):
        try:
            paths = unreal.EditorAssetLibrary.list_assets(folder, recursive=True, include_folder=False) or []
        except Exception:
            paths = []
        for p in paths:
            clean = p.split(".")[0]
            if "coin" not in clean.lower():
                continue
            asset = unreal.EditorAssetLibrary.load_asset(clean)
            if isinstance(asset, unreal.StaticMesh):
                return asset, clean
    # Asset registry fallback
    try:
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        assets = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "StaticMesh"), True) or []
        for ad in assets:
            name = str(ad.asset_name)
            path = str(ad.package_name)
            if name.lower() == "coin" or path.endswith("/Coin"):
                loaded = unreal.EditorAssetLibrary.load_asset(path)
                if isinstance(loaded, unreal.StaticMesh):
                    return loaded, path
    except Exception as e:
        log(f"asset registry scan err: {e}")
    return None, None


def extract_import_filenames(mesh):
    names = []
    aid = safe_get(mesh, "asset_import_data")
    log(f"asset_import_data type={type(aid).__name__ if aid else None}")
    if not aid:
        return names
    for meth in ("script_get_first_filename", "get_first_filename", "get_source_filename"):
        if hasattr(aid, meth):
            try:
                v = getattr(aid, meth)()
                log(f"  {meth}()={v!r}")
                if v:
                    names.append(str(v))
            except Exception as e:
                log(f"  {meth} err: {e}")
    for meth in ("script_extract_filenames", "extract_filenames"):
        if hasattr(aid, meth):
            try:
                vals = list(getattr(aid, meth)() or [])
                log(f"  {meth}()={vals}")
                for v in vals:
                    if v:
                        names.append(str(v))
            except Exception as e:
                log(f"  {meth} err: {e}")
    # Source file array used by UAssetImportData
    try:
        srcs = safe_get(aid, "source_data") or safe_get(aid, "source_files")
        log(f"  source_files={srcs}")
        if srcs:
            for s in list(srcs):
                for attr in ("relative_filename", "file_path", "filename"):
                    try:
                        v = s.get_editor_property(attr) if hasattr(s, "get_editor_property") else getattr(s, attr, None)
                    except Exception:
                        v = getattr(s, attr, None)
                    if v:
                        names.append(str(v))
                        log(f"  source.{attr}={v}")
    except Exception as e:
        log(f"  source_files err: {e}")
    # Interchange pipelines stored on import data
    try:
        pipelines = None
        if hasattr(aid, "get_pipelines"):
            pipelines = aid.get_pipelines()
        if pipelines is None:
            pipelines = safe_get(aid, "pipelines")
        if pipelines:
            log(f"  stored pipelines={[type(p).__name__ for p in pipelines]}")
            for p in pipelines:
                scale = safe_get(p, "import_offset_uniform_scale")
                log(f"    {type(p).__name__} import_offset_uniform_scale={scale}")
    except Exception as e:
        log(f"  pipelines err: {e}")
    # de-dupe
    out = []
    seen = set()
    for n in names:
        n = n.strip().strip('"')
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def walk_search_glbs(filename_hints):
    found = []
    hints_l = [os.path.basename(h).lower() for h in filename_hints if h]
    searched = []
    for root in SEARCH_ROOTS:
        if not root or not os.path.isdir(root):
            log(f"SEARCH skip missing {root}")
            continue
        searched.append(root)
        log(f"SEARCH walking {root}")
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                # skip huge / irrelevant trees
                low = dirpath.replace("\\", "/").lower()
                if any(x in low for x in ("/node_modules", "/.git", "/saved/webcache", "/intermediate", "/binaries", "/deriveddatacache")):
                    dirnames[:] = []
                    continue
                if root.replace("\\", "/").rstrip("/").lower().endswith("meat_ross"):
                    # only Art + Content/Office/Models/Coin at project root
                    if "/art" not in low and "/models/coin" not in low:
                        dirnames[:] = [d for d in dirnames if d.lower() in ("art", "content", "office", "models", "coin")]
                for fn in filenames:
                    ext = os.path.splitext(fn)[1].lower()
                    if ext not in (".glb", ".gltf"):
                        continue
                    full = os.path.join(dirpath, fn)
                    score = 0
                    fl = fn.lower()
                    if "coin" in fl:
                        score += 10
                    if any(h and h == fl for h in hints_l):
                        score += 50
                    if any(h and h in fl for h in hints_l):
                        score += 5
                    found.append((score, full))
        except Exception as e:
            log(f"SEARCH err {root}: {e}")
    found.sort(key=lambda x: (-x[0], x[1].lower()))
    log(f"SEARCH glb/gltf hits={[(s, p) for s, p in found[:20]]}")
    return found, searched


def resolve_source(mesh):
    import_names = extract_import_filenames(mesh) if mesh else []
    log(f"import_filenames={import_names}")
    for n in import_names:
        if os.path.isfile(n):
            log(f"SOURCE from import data (exists): {n}")
            return n, "asset_import_data"
        # maybe relative
        for root in SEARCH_ROOTS:
            cand = os.path.join(root, n) if not os.path.isabs(n) else n
            if os.path.isfile(cand):
                log(f"SOURCE resolved relative: {cand}")
                return cand, "asset_import_data_relative"
        base = os.path.basename(n)
        for root in SEARCH_ROOTS:
            if not os.path.isdir(root):
                continue
            cand = os.path.join(root, base)
            if os.path.isfile(cand):
                log(f"SOURCE basename in {root}: {cand}")
                return cand, "basename_in_search_root"

    # Interchange can_reimport
    try:
        mgr = unreal.InterchangeManager.get_interchange_manager_scripted()
        out = unreal.Array(str)
        ok = mgr.can_reimport(mesh, out)
        log(f"can_reimport={ok} files={list(out)}")
        for n in list(out):
            if n and os.path.isfile(n):
                log(f"SOURCE from can_reimport: {n}")
                return n, "can_reimport"
            if n:
                import_names.append(n)
    except Exception as e:
        log(f"can_reimport err: {e}")

    for cand in KNOWN_CANDIDATES:
        if os.path.isfile(cand):
            log(f"SOURCE from known candidate: {cand}")
            return cand, "known_candidate"

    hits, _searched = walk_search_glbs(import_names)
    if hits:
        best = hits[0]
        if best[0] >= 10 and os.path.isfile(best[1]):
            log(f"SOURCE from disk search (score={best[0]}): {best[1]}")
            return best[1], "disk_search_coin_name"
    log("SOURCE not found")
    return None, None


def configure_pipeline(pipeline):
    """Set Interchange generic pipeline to 0.1 uniform scale."""
    applied = []

    def setp(obj, prop, val):
        try:
            obj.set_editor_property(prop, val)
            applied.append(f"{type(obj).__name__}.{prop}={val}")
            return True
        except Exception as e:
            log(f"  set {type(obj).__name__}.{prop} failed: {e}")
            return False

    setp(pipeline, "import_offset_uniform_scale", float(UNIFORM_SCALE))
    setp(pipeline, "use_source_name_for_asset", False)
    setp(pipeline, "asset_name", ASSET_NAME)
    # Prefer applying pipeline properties so scale is not ignored on reimport
    if hasattr(unreal, "ReimportStrategyFlags"):
        flags = list(unreal.ReimportStrategyFlags)
        log(f"ReimportStrategyFlags={flags}")
        chosen = getattr(unreal.ReimportStrategyFlags, "APPLY_PIPELINE_PROPERTIES", None)
        if chosen is not None:
            setp(pipeline, "reimport_strategy", chosen)
    mesh_pipe = safe_get(pipeline, "mesh_pipeline")
    if mesh_pipe:
        setp(mesh_pipe, "build_scale3d", unreal.Vector(UNIFORM_SCALE, UNIFORM_SCALE, UNIFORM_SCALE))
        setp(mesh_pipe, "import_static_meshes", True)
        setp(mesh_pipe, "combine_static_meshes", True)
        setp(mesh_pipe, "collision", True)
    log(f"pipeline applied: {applied}")
    return applied


def make_generic_pipeline():
    pipeline = unreal.InterchangeGenericAssetsPipeline()
    configure_pipeline(pipeline)
    return pipeline


def import_via_interchange(src, mesh, dest_path):
    mgr = unreal.InterchangeManager.get_interchange_manager_scripted()
    source = mgr.create_source_data(src)
    params = unreal.ImportAssetParameters()
    params.set_editor_property("is_automated", True)
    params.set_editor_property("replace_existing", True)
    params.set_editor_property("destination_name", ASSET_NAME)
    if mesh:
        try:
            params.set_editor_property("reimport_asset", mesh)
        except Exception as e:
            log(f"reimport_asset set err: {e}")
    pipeline = make_generic_pipeline()
    stack = None
    try:
        stack = unreal.InterchangePipelineStackOverride()
        stack.add_pipeline(pipeline)
        log("added pipeline via InterchangePipelineStackOverride")
    except Exception as e:
        log(f"stack override err: {e}")
    try:
        params.set_editor_property("override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())])
        log(f"override_pipelines={params.get_editor_property('override_pipelines')}")
    except Exception as e:
        log(f"override_pipelines set err: {e}")

    imported = []
    ok = False
    # Prefer import_asset (sync) with OutImportedObjects if the python binding accepts it
    try:
        ok = bool(mgr.import_asset(dest_path, source, params))
        log(f"InterchangeManager.import_asset -> {ok}")
    except TypeError:
        try:
            out = []
            ok = bool(mgr.import_asset(dest_path, source, params, out))
            imported = list(out)
            log(f"InterchangeManager.import_asset(out) -> {ok} objs={imported}")
        except Exception as e:
            log(f"import_asset variant err: {e}")
    except Exception as e:
        log(f"import_asset err: {e}")

    if not ok and mesh:
        try:
            ok = bool(mgr.reimport_asset(mesh, params))
            log(f"InterchangeManager.reimport_asset -> {ok}")
        except TypeError:
            try:
                out = []
                ok = bool(mgr.reimport_asset(mesh, params, out))
                imported = list(out)
                log(f"InterchangeManager.reimport_asset(out) -> {ok} objs={imported}")
            except Exception as e:
                log(f"reimport_asset variant err: {e}")
        except Exception as e:
            log(f"reimport_asset err: {e}")

    try:
        if hasattr(mgr, "wait_until_all_tasks_done"):
            mgr.wait_until_all_tasks_done(True)
            log("wait_until_all_tasks_done")
    except Exception as e:
        log(f"wait err: {e}")
    return ok, imported


def import_via_asset_task(src, dest_path):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", src)
    task.set_editor_property("destination_path", dest_path)
    task.set_editor_property("destination_name", ASSET_NAME)
    task.set_editor_property("replace_existing", True)
    try:
        task.set_editor_property("replace_existing_settings", True)
    except Exception:
        pass
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    # Interchange options
    pipeline = make_generic_pipeline()
    options_set = False
    try:
        stack = unreal.InterchangePipelineStackOverride()
        stack.add_pipeline(pipeline)
        task.set_editor_property("options", stack)
        options_set = True
        log("AssetImportTask.options=InterchangePipelineStackOverride")
    except Exception as e:
        log(f"task.options stack err: {e}")
    if not options_set:
        try:
            task.set_editor_property("options", pipeline)
            options_set = True
            log("AssetImportTask.options=InterchangeGenericAssetsPipeline")
        except Exception as e:
            log(f"task.options pipeline err: {e}")
    # Fbx-style fallback if factory exposes it
    if not options_set and hasattr(unreal, "FbxImportUI"):
        try:
            ui = unreal.FbxImportUI()
            ui.set_editor_property("automated_import_should_detect_type", False)
            ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
            sm = safe_get(ui, "static_mesh_import_data")
            if sm:
                for prop in ("import_uniform_scale", "import_translation"):
                    if prop == "import_uniform_scale":
                        sm.set_editor_property(prop, float(UNIFORM_SCALE))
                log("FbxImportUI.static_mesh_import_data.import_uniform_scale=0.1")
            task.set_editor_property("options", ui)
            options_set = True
        except Exception as e:
            log(f"FbxImportUI err: {e}")
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = list(getattr(task, "imported_object_paths", []) or [])
    log(f"AssetImportTask imported_object_paths={paths}")
    return bool(paths), paths


def reset_coin_actor_scales(mesh):
    reset = []
    actors = all_level_actors()
    for a in actors:
        label = actor_label(a)
        if label != "Coin" and "coin" not in label.lower():
            continue
        uses_mesh = False
        try:
            comps = list(a.get_components_by_class(unreal.StaticMeshComponent) or [])
        except Exception:
            comps = []
            smc = safe_get(a, "static_mesh_component")
            if smc:
                comps = [smc]
        for c in comps:
            sm = safe_get(c, "static_mesh")
            if sm is None:
                continue
            try:
                same = sm == mesh or sm.get_path_name().split(".")[0] == mesh.get_path_name().split(".")[0]
            except Exception:
                same = False
            if same or (label == "Coin"):
                uses_mesh = True
                break
        if not uses_mesh and label != "Coin":
            continue
        try:
            a.modify()
        except Exception:
            pass
        old = a.get_actor_scale3d()
        a.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
        new = a.get_actor_scale3d()
        msg = (
            f"actor={label} name={a.get_name()} "
            f"scale {old.x:.4f},{old.y:.4f},{old.z:.4f} -> {new.x:.4f},{new.y:.4f},{new.z:.4f} "
            f"loc=({a.get_actor_location().x:.1f},{a.get_actor_location().y:.1f},{a.get_actor_location().z:.1f})"
        )
        log(msg)
        reset.append(msg)
    if not reset:
        log("WARN: no Coin actors found to reset scale")
    return reset


def save_all(mesh_pkg):
    mesh_ok = False
    level_ok = False
    try:
        mesh_ok = bool(unreal.EditorAssetLibrary.save_asset(mesh_pkg, only_if_is_dirty=False))
        log(f"save mesh {mesh_pkg} -> {mesh_ok}")
    except Exception as e:
        log(f"save mesh err: {e}")
    try:
        # also save parent Coin folder assets (materials/textures created by import)
        folder = "/Game/Office/Models/Coin"
        for p in unreal.EditorAssetLibrary.list_assets(folder, recursive=True, include_folder=False) or []:
            clean = p.split(".")[0]
            try:
                unreal.EditorAssetLibrary.save_asset(clean, only_if_is_dirty=False)
            except Exception:
                pass
        log("saved Coin folder assets")
    except Exception as e:
        log(f"save folder err: {e}")
    try:
        level_ok = bool(unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level())
        log(f"save_current_level -> {level_ok}")
    except Exception as e:
        log(f"save_current_level err: {e}")
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("save_dirty_packages")
    except Exception as e:
        log(f"save_dirty err: {e}")
    return mesh_ok, level_ok


def ensure_office_map():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    wname = world.get_name() if world else ""
    log(f"world={wname}")
    if "office" not in (wname or "").lower():
        log(f"Loading {MAP_PATH}")
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        log(f"world after load={world.get_name() if world else None}")


def main():
    log("=== start ===")
    ensure_office_map()
    mesh, pkg = find_coin_mesh()
    log(f"mesh={pkg} loaded={bool(mesh)}")
    bounds_before = mesh_bounds_str(mesh) if mesh else "NO_MESH"
    log(f"BOUNDS_BEFORE {bounds_before}")

    src, how = resolve_source(mesh)
    log(f"SOURCE_PATH={src} via={how}")
    if not src or not os.path.isfile(src):
        hits, searched = walk_search_glbs([])
        log("ERROR: source GLB/GLTF not found. Do not invent a path.")
        log(f"searched_roots={SEARCH_ROOTS}")
        log(f"search_hits={hits[:30]}")
        flush_report()
        return

    dest = DEST_PATH
    if pkg:
        dest = pkg.rsplit("/", 1)[0]
    unreal.EditorAssetLibrary.make_directory(dest)

    ok = False
    try:
        ok, imported = import_via_interchange(src, mesh, dest)
        log(f"interchange ok={ok} imported={imported}")
    except Exception:
        log(traceback.format_exc())
        ok = False

    if not ok:
        log("fallback AssetImportTask")
        try:
            ok, paths = import_via_asset_task(src, dest)
            log(f"task ok={ok} paths={paths}")
        except Exception:
            log(traceback.format_exc())

    mesh2, pkg2 = find_coin_mesh()
    if mesh2:
        mesh, pkg = mesh2, pkg2
    bounds_after = mesh_bounds_str(mesh) if mesh else "NO_MESH"
    log(f"BOUNDS_AFTER {bounds_after}")
    log(f"reimport_succeeded={ok and mesh is not None}")

    reset = reset_coin_actor_scales(mesh) if mesh else []
    mesh_ok, level_ok = save_all(pkg or MESH_PKG)
    if not reset:
        log("level save attempted anyway; no Coin actors were scaled")
    log(f"SAVE mesh_ok={mesh_ok} level_ok={level_ok} actor_scale_reset={bool(reset)}")
    log("=== done ===")
    flush_report()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log(traceback.format_exc())
        flush_report()
        raise
