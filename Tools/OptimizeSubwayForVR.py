# Optimize Subway.umap for VR: cut light/shadow/fog/godray/PP cost.
# Run via UnrealEditor-Cmd -ExecutePythonScript

import unreal

MAP_PATH = "/Game/SubwayTrain/Maps/Subway"
OVERHEAD_BP = "/Game/SubwayTrain/Blueprints/BP_Overheadlight_01"
LOG = []


def log(msg):
    unreal.log(f"[OptimizeSubwayForVR] {msg}")
    LOG.append(msg)


def set_bool(obj, name, value):
    if obj is None:
        return False
    try:
        if obj.get_editor_property(name) == value:
            return False
        obj.set_editor_property(name, value)
        return True
    except Exception:
        return False


def set_float(obj, name, value):
    if obj is None:
        return False
    try:
        obj.set_editor_property(name, float(value))
        return True
    except Exception:
        return False


def disable_light_cost(component):
    changed = False
    if component is None:
        return False
    changed |= set_bool(component, "cast_shadows", False)
    changed |= set_bool(component, "cast_static_shadows", False)
    changed |= set_bool(component, "cast_dynamic_shadows", False)
    changed |= set_bool(component, "cast_volumetric_shadow", False)
    changed |= set_bool(component, "affect_translucent_lighting", False)
    changed |= set_bool(component, "transmission", False)
    # Soften expensive local lights a bit
    try:
        if hasattr(component, "set_editor_property"):
            set_bool(component, "use_inverse_squared_falloff", True)
    except Exception:
        pass
    return changed


def optimize_lights(world):
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Light)
    changed = 0
    cinematic_hidden = 0
    for actor in actors:
        folder = ""
        try:
            folder = str(actor.get_folder_path())
        except Exception:
            pass

        # Cinematic movable lights are especially expensive in VR
        if "cinmeatic" in folder.lower() or "cinematic" in folder.lower() or "moveable" in folder.lower():
            if set_bool(actor, "hidden", True) or set_bool(actor, "b_hidden", True):
                cinematic_hidden += 1
            try:
                actor.set_actor_hidden_in_game(True)
                actor.set_actor_enable_collision(False)
                cinematic_hidden += 1
            except Exception:
                pass
            continue

        # Prefer Static mobility when possible
        try:
            root = actor.root_component
            if root and hasattr(unreal, "ComponentMobility"):
                root.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
        except Exception:
            pass

        # Disable shadows on all light components under the actor
        comps = []
        try:
            comps = actor.get_components_by_class(unreal.LightComponent)
        except Exception:
            comps = []
        if not comps:
            try:
                comps = [actor.light_component]
            except Exception:
                comps = []
        for comp in comps:
            if disable_light_cost(comp):
                changed += 1

    log(f"Lights shadow-stripped: {changed}, cinematic lights hidden: {cinematic_hidden}")


def optimize_overhead_blueprint():
    bp = unreal.EditorAssetLibrary.load_asset(OVERHEAD_BP)
    if not bp:
        log(f"Could not load {OVERHEAD_BP}")
        return

    changed = 0
    try:
        # Class defaults / SCS components
        cdo = unreal.get_default_object(bp.generated_class())
        comps = []
        try:
            comps = cdo.get_components_by_class(unreal.LightComponent)
        except Exception:
            comps = []
        for comp in comps:
            if disable_light_cost(comp):
                changed += 1
    except Exception as e:
        log(f"Overhead BP CDO tweak failed: {e}")

    # Also walk simple construction script nodes via SubobjectDataSubsystem when available
    try:
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
        for handle in handles:
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data)
            if isinstance(obj, unreal.LightComponent):
                if disable_light_cost(obj):
                    changed += 1
    except Exception as e:
        log(f"Overhead BP subobject tweak skipped: {e}")

    if changed:
        unreal.EditorAssetLibrary.save_asset(OVERHEAD_BP)
    log(f"BP_Overheadlight_01 light components optimized: {changed}")


def hide_expensive_meshes(world):
    keywords = (
        "godray",
        "god_ray",
        "fog_plane",
        "polyplane",
        "sm_godray",
        "sm_fog_plane",
        "sm_polyplane",
    )
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor)
    hidden = 0
    for actor in actors:
        name = actor.get_name().lower()
        mesh_path = ""
        try:
            mesh = actor.static_mesh_component.static_mesh
            if mesh:
                mesh_path = unreal.EditorAssetLibrary.get_path_name_for_loaded_asset(mesh).lower()
        except Exception:
            pass
        hay = f"{name} {mesh_path}"
        if any(k in hay for k in keywords):
            try:
                actor.set_actor_hidden_in_game(True)
                actor.set_actor_enable_collision(False)
                set_bool(actor, "hidden", True)
                hidden += 1
            except Exception:
                pass
    log(f"Hidden godray/fog plane meshes: {hidden}")


def optimize_fog(world):
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ExponentialHeightFog)
    changed = 0
    for actor in actors:
        comp = None
        try:
            comp = actor.component
        except Exception:
            pass
        if comp is None:
            try:
                comps = actor.get_components_by_class(unreal.ExponentialHeightFogComponent)
                comp = comps[0] if comps else None
            except Exception:
                comp = None
        if comp is None:
            continue
        if set_bool(comp, "volumetric_fog", False):
            changed += 1
        set_float(comp, "fog_density", 0.01)
        set_float(comp, "volumetric_fog_extinction_scale", 0.0)
    log(f"ExponentialHeightFog volumetric disabled: {changed}")


def optimize_post_process(world):
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PostProcessVolume)
    changed = 0
    for actor in actors:
        try:
            settings = actor.settings
            # Turn off heavy VR-unfriendly effects when possible
            for prop, value in (
                ("mobile_ambient_occlusion", False),
                ("ambient_occlusion_intensity", 0.0),
                ("bloom_intensity", 0.15),
                ("depth_of_field_fstop", 32.0),
                ("lens_flare_intensity", 0.0),
                ("motion_blur_amount", 0.0),
                ("screen_space_reflection_intensity", 30.0),
            ):
                try:
                    settings.set_editor_property(prop, value)
                except Exception:
                    pass
            actor.set_editor_property("settings", settings)
            # Prefer unbound volumes not fighting each other: keep enabled but cheaper
            changed += 1
        except Exception as e:
            log(f"PP tweak failed on {actor.get_name()}: {e}")
    log(f"PostProcess volumes softened: {changed}")


def cull_reflection_captures(world, keep=4):
    spheres = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SphereReflectionCapture))
    boxes = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.BoxReflectionCapture))
    all_caps = spheres + boxes
    deleted = 0
    # Keep first N, delete the rest (reflection captures are costly to update with many dynamic lights)
    for actor in all_caps[keep:]:
        try:
            actor.destroy_actor()
            deleted += 1
        except Exception:
            try:
                unreal.EditorLevelLibrary.destroy_actor(actor)
                deleted += 1
            except Exception:
                pass
    log(f"Reflection captures kept={min(keep, len(all_caps))}, deleted={deleted}, total_before={len(all_caps)}")


def optimize_underbody(world):
    # Exterior underbody detail is rarely seen from inside the car in VR
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    hidden = 0
    for actor in actors:
        name = actor.get_name().lower()
        cls = actor.get_class().get_name().lower()
        if "underbody" in name or "underbody" in cls or "bogie" in name:
            try:
                actor.set_actor_hidden_in_game(True)
                hidden += 1
            except Exception:
                pass
    log(f"Hidden underbody/exterior detail actors: {hidden}")


def main():
    log("Loading Subway map...")
    if not unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH):
        # Fallback API
        try:
            unreal.EditorLevelLibrary.load_level(MAP_PATH)
        except Exception as e:
            log(f"Failed to load map: {e}")
            return

    world = unreal.EditorLevelLibrary.get_editor_world()
    if world is None:
        log("No editor world")
        return

    optimize_overhead_blueprint()
    optimize_lights(world)
    hide_expensive_meshes(world)
    optimize_fog(world)
    optimize_post_process(world)
    cull_reflection_captures(world, keep=4)
    optimize_underbody(world)

    # Save current level
    try:
        unreal.EditorLevelLibrary.save_current_level()
    except Exception:
        pass
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception:
        unreal.EditorAssetLibrary.save_directory("/Game/SubwayTrain")

    log("Done.")
    for line in LOG:
        print(line)


if __name__ == "__main__":
    main()
