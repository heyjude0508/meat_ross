# Fix Office.umap darkness: enable FLICKER spotlights + soften exposure clamp.
import unreal

MAP_PATH = "/Game/Office/Maps/Office"
FLICKER_BP = "/Game/Office/Blueprints/BP_Ceiling_300_FLICKER"
ON_MAT = "/Game/Office/Materials/Mi_CeilingLight_01a"  # emissive 900


def log(msg):
    unreal.log(f"[FixOfficeLighting] {msg}")


def safe_get(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def safe_set(obj, name, value):
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception:
        return False


def enable_light(comp):
    changed = False
    if safe_get(comp, "visible") is False:
        if safe_set(comp, "visible", True):
            changed = True
    if safe_get(comp, "hidden_in_game") is True:
        if safe_set(comp, "hidden_in_game", False):
            changed = True
    if safe_get(comp, "affects_world") is False:
        if safe_set(comp, "affects_world", True):
            changed = True
    # Ensure editor visibility too
    try:
        if hasattr(comp, "set_visibility"):
            comp.set_visibility(True, True)
            changed = True
    except Exception:
        pass
    try:
        if hasattr(comp, "set_hidden_in_game"):
            comp.set_hidden_in_game(False, True)
            changed = True
    except Exception:
        pass
    return changed


def fix_bp_defaults():
    """Make FLICKER CDO / newly placed actors start with light on."""
    bp = unreal.EditorAssetLibrary.load_asset(FLICKER_BP)
    if not bp:
        log("WARN: cannot load FLICKER BP")
        return
    # Spawn temp, mutate components, then copy values onto existing map actors is enough.
    # Also try to mutate SCS via spawning and editing defaults through generated class is limited;
    # map-instance fix is the reliable path. Keep BP compile/save for dirty refs.
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as e:
        log(f"compile FLICKER: {e}")
    unreal.EditorAssetLibrary.save_asset(FLICKER_BP, only_if_is_dirty=True)
    log("FLICKER BP touched/saved")


def fix_map():
    log(f"Loading {MAP_PATH}")
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

    lights_fixed = 0
    lights_seen = 0
    mats_fixed = 0
    on_mat = unreal.EditorAssetLibrary.load_asset(ON_MAT)

    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        cls = actor.get_class().get_name()
        if "Ceiling_300_FLICKER" not in cls:
            continue
        for comp in actor.get_components_by_class(unreal.LightComponent):
            lights_seen += 1
            if enable_light(comp):
                lights_fixed += 1
                actor.modify()
        # Keep emissive-on material on fixture mesh if somehow swapped
        if on_mat:
            for mesh in actor.get_components_by_class(unreal.StaticMeshComponent):
                if "CeilingLight" in mesh.get_name() or "CeilingLight" in str(safe_get(mesh, "static_mesh")):
                    try:
                        cur = mesh.get_material(0)
                        if cur and "01b" in cur.get_path_name():
                            mesh.set_material(0, on_mat)
                            mats_fixed += 1
                            actor.modify()
                    except Exception:
                        pass

    log(f"FLICKER lights seen={lights_seen} fixed={lights_fixed} mats_swapped_from_01b={mats_fixed}")

    # Soften unbound PostProcessVolume exposure clamp that keeps dark scenes dark
    ppv_fixed = 0
    for ppv in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PostProcessVolume):
        unbound = safe_get(ppv, "unbound")
        if unbound is None:
            unbound = safe_get(ppv, "bUnbound")
        settings = safe_get(ppv, "settings")
        if not settings:
            continue
        min_b = safe_get(settings, "auto_exposure_min_brightness")
        max_b = safe_get(settings, "auto_exposure_max_brightness")
        # Only adjust the unbound global volume with harsh min brightness
        if unbound and min_b is not None and min_b >= 4.0:
            log(f"PPV {ppv.get_actor_label()} unbound min={min_b} max={max_b} -> loosen")
            safe_set(settings, "auto_exposure_min_brightness", 0.1)
            # Keep max reasonably high
            if max_b is not None and max_b < 10:
                safe_set(settings, "auto_exposure_max_brightness", 20.0)
            safe_set(settings, "override_auto_exposure_min_brightness", True)
            safe_set(settings, "override_auto_exposure_max_brightness", True)
            # Write settings back
            safe_set(ppv, "settings", settings)
            ppv.modify()
            ppv_fixed += 1
    log(f"PPV fixed={ppv_fixed}")

    # Recapture skylight
    for sky in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SkyLight):
        for comp in sky.get_components_by_class(unreal.SkyLightComponent):
            try:
                # Prefer realtime for Lumen indoor fill if available
                if safe_get(comp, "real_time_capture") is False:
                    safe_set(comp, "real_time_capture", True)
                    log("SkyLight realtime capture enabled")
                if hasattr(comp, "recapture_sky"):
                    comp.recapture_sky()
                    log("SkyLight recaptured")
                sky.modify()
            except Exception as e:
                log(f"SkyLight fix err: {e}")

    # Ensure editor scalability isn't stuck low in this session
    for cmd in (
        "sg.GlobalIlluminationQuality 3",
        "sg.ShadowQuality 3",
        "sg.PostProcessQuality 3",
        "sg.ReflectionQuality 3",
        "r.DynamicGlobalIlluminationMethod 1",
        "r.ReflectionMethod 1",
    ):
        unreal.SystemLibrary.execute_console_command(world, cmd)
        log(f"exec {cmd}")

    # Save
    ok = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    log(f"Save level ok={ok}")

    # Verify
    vis_true = 0
    vis_false = 0
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if "Ceiling_300_FLICKER" not in actor.get_class().get_name():
            continue
        for comp in actor.get_components_by_class(unreal.LightComponent):
            if safe_get(comp, "visible") is True and safe_get(comp, "hidden_in_game") is not True:
                vis_true += 1
            else:
                vis_false += 1
    log(f"VERIFY lights on={vis_true} still_off={vis_false}")
    log("Done")


def main():
    fix_bp_defaults()
    fix_map()


if __name__ == "__main__":
    main()
