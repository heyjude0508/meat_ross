"""Dump selected/named tripo_part StaticMeshActors in the current editor world."""
import unreal

def log(m):
    unreal.log(f"[StrongboxDump] {m}")


def bounds_of(actor):
    origin, extent = actor.get_actor_bounds(False)
    return origin, extent


def main():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    hits = []
    for a in actors:
        name = a.get_actor_label()
        if "tripo_part" in name.lower() or "tripo_part" in a.get_name().lower():
            hits.append(a)

    sel = list(unreal.EditorLevelLibrary.get_selected_level_actors() or [])
    log(f"world={world.get_name()} selected={len(sel)} tripo_hits={len(hits)}")
    for a in sel:
        log(f"SEL {a.get_actor_label()} class={a.get_class().get_name()} loc={a.get_actor_location()} rot={a.get_actor_rotation()}")

    pool = hits if hits else sel
    for a in pool:
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        origin, extent = bounds_of(a)
        mesh = None
        mesh_path = ""
        try:
            smc = a.static_mesh_component
            mesh = smc.static_mesh if smc else None
            mesh_path = mesh.get_path_name() if mesh else ""
        except Exception as e:
            log(f"  mesh err {e}")
        vol = extent.x * extent.y * extent.z * 8.0
        log(
            f"ACTOR label={a.get_actor_label()} name={a.get_name()} "
            f"loc=({loc.x:.1f},{loc.y:.1f},{loc.z:.1f}) "
            f"rot=({rot.pitch:.1f},{rot.yaw:.1f},{rot.roll:.1f}) "
            f"origin=({origin.x:.1f},{origin.y:.1f},{origin.z:.1f}) "
            f"extent=({extent.x:.1f},{extent.y:.1f},{extent.z:.1f}) "
            f"vol={vol:.0f} mesh={mesh_path}"
        )
        if mesh:
            try:
                box = mesh.get_bounding_box()
                mn, mx = box.min, box.max
                log(
                    f"  meshBox min=({mn.x:.1f},{mn.y:.1f},{mn.z:.1f}) "
                    f"max=({mx.x:.1f},{mx.y:.1f},{mx.z:.1f}) "
                    f"size=({mx.x-mn.x:.1f},{mx.y-mn.y:.1f},{mx.z-mn.z:.1f})"
                )
            except Exception as e:
                log(f"  meshBox err {e}")


if __name__ == "__main__":
    main()
