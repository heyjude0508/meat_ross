# Inspect Office ceiling light BPs and map instances.
import unreal

MAP = "/Game/Office/Maps/Office"
OVERVIEW = "/Game/Office/Maps/Overview"
BPS = [
    "/Game/Office/Blueprints/BP_Ceiling_300_FLICKER",
    "/Game/Office/Blueprints/BP_Ceiling_300_ON",
    "/Game/Office/Blueprints/BP_Ceiling_300_OFF",
]


def log(m):
    unreal.log(f"[InspectCeiling] {m}")


def safe_get(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def dump_cdo(path):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if not asset:
        log(f"MISSING {path}")
        return
    log(f"=== BP {path} type={asset.get_class().get_name()} ===")
    try:
        gen = asset.generated_class()
        cdo = unreal.get_default_object(gen) if gen else None
    except Exception as e:
        log(f"  generated_class err: {e}")
        cdo = None
    if cdo is None:
        return
    # Properties on CDO
    for prop in (
        "light_on",
        "b_light_on",
        "is_on",
        "b_is_on",
        "flicker",
        "b_flicker",
        "intensity",
        "start_on",
        "b_start_on",
        "enabled",
        "b_enabled",
    ):
        v = safe_get(cdo, prop)
        if v is not None:
            log(f"  CDO.{prop}={v}")
    # Components
    comps = cdo.get_components_by_class(unreal.ActorComponent)
    for c in comps:
        cls = c.get_class().get_name()
        name = c.get_name()
        if "Light" in cls or "Mesh" in cls or "Spot" in cls or "Point" in cls:
            vis = safe_get(c, "visible")
            intens = safe_get(c, "intensity")
            affect = safe_get(c, "affects_world")
            mat = None
            try:
                if hasattr(c, "get_material"):
                    mat = c.get_material(0)
            except Exception:
                pass
            log(
                f"  Comp {name} ({cls}) visible={vis} intensity={intens} "
                f"affects={affect} mat0={mat}"
            )
    # Graph node names (events / timelines)
    try:
        graph = unreal.BlueprintEditorLibrary.find_event_graph(asset)
        if graph:
            nodes = graph.get_editor_property("nodes") or []
            interesting = []
            for n in nodes:
                nm = n.get_name()
                cls = n.get_class().get_name()
                if any(
                    k in nm or k in cls
                    for k in (
                        "BeginPlay",
                        "Construct",
                        "Timeline",
                        "SetVisibility",
                        "SetHidden",
                        "Intensity",
                        "Light",
                        "Flicker",
                        "Delay",
                        "Branch",
                        "CustomEvent",
                    )
                ):
                    interesting.append(f"{cls}:{nm}")
            log(f"  EventGraph interesting nodes ({len(interesting)}): {interesting[:40]}")
    except Exception as e:
        log(f"  graph err: {e}")


def count_map(path):
    log(f"Loading map {path}")
    unreal.EditorLoadingAndSavingUtils.load_map(path)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    counts = {"ON": 0, "OFF": 0, "FLICKER": 0, "other_light": 0}
    vis_true = 0
    vis_false = 0
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        cls = a.get_class().get_name()
        if "Ceiling_300" not in cls and "Projector" not in cls:
            continue
        if "FLICKER" in cls:
            counts["FLICKER"] += 1
        elif cls.endswith("ON_C") or "_ON_C" in cls or cls == "BP_Ceiling_300_ON_C":
            counts["ON"] += 1
        elif "OFF" in cls:
            counts["OFF"] += 1
        else:
            counts["other_light"] += 1
        for c in a.get_components_by_class(unreal.LightComponent):
            v = safe_get(c, "visible")
            if v is True:
                vis_true += 1
            elif v is False:
                vis_false += 1
    log(f"Map counts={counts} light_visible True={vis_true} False={vis_false}")


def main():
    for p in BPS:
        dump_cdo(p)
    count_map(MAP)
    count_map(OVERVIEW)
    log("Done")


if __name__ == "__main__":
    main()
