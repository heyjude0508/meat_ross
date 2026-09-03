# Create a Y-mirrored copy of SM_Cubicles_Blockout93 in Office.umap (UE 5.7).
import unreal

MAP_PATH = "/Game/Office/Maps/Office"
SRC_LABEL = "SM_Cubicles_Blockout93"
DST_LABEL = "SM_Cubicles_Blockout93_Mirrored"
# From live session: 93@(1666.26,-1980,10), former neighbor 94 was 200uu toward -Y
OFFSET_Y = -200.0


def log(msg):
    unreal.log(f"[MirrorCubicle] {msg}")


def v3(v):
    return (round(float(v.x), 2), round(float(v.y), 2), round(float(v.z), 2))


def find_label(world, label):
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if a.get_actor_label() == label:
            return a
    return None


def get_mesh_comp(actor):
    return actor.get_component_by_class(unreal.StaticMeshComponent)


def spawn_mirrored_from(src):
    """Spawn a new StaticMeshActor copying mesh/materials from src, mirrored on Y."""
    smc = get_mesh_comp(src)
    if not smc or not smc.static_mesh:
        raise RuntimeError("source has no StaticMesh")

    loc = src.get_actor_location()
    rot = src.get_actor_rotation()
    scale = src.get_actor_scale3d()

    new_loc = unreal.Vector(float(loc.x), float(loc.y) + OFFSET_Y, float(loc.z))
    new_scale = unreal.Vector(float(scale.x), -float(scale.y) if float(scale.y) != 0 else -1.0, float(scale.z))

    # Prefer EditorActorSubsystem.spawn_actor_from_class / EditorLevelLibrary
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    dup = None
    try:
        dup = actor_sub.spawn_actor_from_class(
            unreal.StaticMeshActor.static_class(), new_loc, rot
        )
    except Exception as e:
        log(f"actor_sub.spawn failed: {e}")
    if not dup:
        dup = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.StaticMeshActor.static_class(), new_loc, rot
        )
    if not dup:
        raise RuntimeError("spawn failed")

    dst_smc = get_mesh_comp(dup)
    dst_smc.set_editor_property("static_mesh", smc.static_mesh)
    try:
        n = smc.get_num_materials()
        for i in range(int(n)):
            dst_smc.set_material(i, smc.get_material(i))
    except Exception as e:
        log(f"copy materials: {e}")

    # Mobility / collision / shadow flags from source when possible
    for prop in (
        "mobility",
        "cast_shadow",
        "collision_enabled",
        "collision_profile_name",
        "generate_overlap_events",
    ):
        try:
            dst_smc.set_editor_property(prop, smc.get_editor_property(prop))
        except Exception:
            pass

    dup.set_actor_location(new_loc, False, True)
    dup.set_actor_rotation(rot, False)
    root = dup.root_component
    root.set_editor_property("relative_scale3d", new_scale)

    try:
        dup.set_actor_label(DST_LABEL)
    except Exception:
        pass
    try:
        folder = src.get_folder_path()
        if folder:
            dup.set_folder_path(folder)
    except Exception:
        pass

    return dup


def main():
    log(f"Loading {MAP_PATH}")
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

    # Remove previous mirrored if re-run
    existing = find_label(world, DST_LABEL)
    if existing:
        log(f"Removing old {DST_LABEL}")
        try:
            unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(existing)
        except Exception:
            existing.destroy_actor()

    src = find_label(world, SRC_LABEL)
    if not src:
        # list cubicle-ish labels for debug
        labels = []
        for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor):
            lb = a.get_actor_label()
            if "Cubicle" in lb or "Blockout" in lb:
                labels.append(lb)
        log(f"ERROR: {SRC_LABEL} not found. sample={labels[:40]}")
        return

    loc = src.get_actor_location()
    rot = src.get_actor_rotation()
    scale = src.get_actor_scale3d()
    smc = get_mesh_comp(src)
    mesh = smc.static_mesh if smc else None
    log(f"src loc={v3(loc)} rot=({rot.roll:.1f},{rot.pitch:.1f},{rot.yaw:.1f}) scale={v3(scale)}")
    log(f"mesh={mesh.get_path_name() if mesh else None}")

    dup = spawn_mirrored_from(src)
    log(
        f"CREATED {dup.get_actor_label()} loc={v3(dup.get_actor_location())} "
        f"scale={v3(dup.get_actor_scale3d())}"
    )

    ok = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    log(f"Save ok={ok}")

    # Verify
    check = find_label(world, DST_LABEL)
    log(f"VERIFY exists={check is not None} scale={v3(check.get_actor_scale3d()) if check else None}")
    log("Done")


if __name__ == "__main__":
    main()
