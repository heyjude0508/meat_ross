# Deeper inspect of Office ceiling light BPs via SCS / CDO reflection.
import unreal

BPS = [
    "/Game/Office/Blueprints/BP_Ceiling_300_FLICKER",
    "/Game/Office/Blueprints/BP_Ceiling_300_ON",
    "/Game/Office/Blueprints/BP_Ceiling_300_OFF",
]


def log(m):
    unreal.log(f"[InspectCeiling2] {m}")


def safe_get(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def dump_bp(path):
    bp = unreal.EditorAssetLibrary.load_asset(path)
    log(f"=== {path} ===")
    if not bp:
        log("  load failed")
        return

    # SimpleConstructionScript nodes
    try:
        scs = bp.get_editor_property("simple_construction_script")
        log(f"  SCS={scs}")
        if scs:
            # Try all nodes
            for attr in ("root_nodes", "all_nodes", "RootNodes", "AllNodes"):
                nodes = safe_get(scs, attr)
                if nodes is not None:
                    log(f"  SCS.{attr} count={len(list(nodes))}")
                    for n in nodes:
                        dump_scs_node(n, "    ")
    except Exception as e:
        log(f"  SCS err: {e}")

    # Generated class CDO via EditorAssetLibrary / subsystem
    try:
        gen = bp.generated_class()
        log(f"  generated_class={gen}")
        if gen:
            cdo = unreal.get_default_object(gen)
            log(f"  CDO={cdo}")
            # Iterate all editor properties that look relevant
            for name in dir(cdo):
                low = name.lower()
                if any(k in low for k in ("light", "flicker", "intensity", "visible", "emissive", "on", "off")):
                    if name.startswith("_"):
                        continue
                    try:
                        val = getattr(cdo, name)
                        if callable(val):
                            continue
                        log(f"  CDO attr {name}={val}")
                    except Exception:
                        pass
            # Component templates via get_editor_property on known names
            for comp_name in (
                "SpotLight",
                "SpotLight1",
                "DefaultSceneRoot",
                "StaticMesh",
                "StaticMeshComponent",
                "CeilingLight",
                "Light",
            ):
                try:
                    comp = cdo.get_editor_property(comp_name) if hasattr(cdo, "get_editor_property") else None
                except Exception:
                    comp = None
                if comp is None:
                    try:
                        comp = getattr(cdo, comp_name, None)
                    except Exception:
                        comp = None
                if comp is not None and not callable(comp):
                    log(
                        f"  CDO.{comp_name}: class={comp.get_class().get_name()} "
                        f"visible={safe_get(comp,'visible')} intensity={safe_get(comp,'intensity')} "
                        f"affects={safe_get(comp,'affects_world')}"
                    )

            # Use component iterator on default object
            try:
                comps = cdo.get_components_by_class(unreal.ActorComponent)
                log(f"  CDO components via get_components_by_class: {len(list(comps))}")
                for c in comps:
                    log(
                        f"    {c.get_name()} ({c.get_class().get_name()}) "
                        f"vis={safe_get(c,'visible')} intens={safe_get(c,'intensity')}"
                    )
            except Exception as e:
                log(f"  CDO comps err: {e}")
    except Exception as e:
        log(f"  gen/cdo err: {e}")

    # Spawn temporary actor to see construction defaults
    try:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        cls = bp.generated_class()
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(cls, unreal.Vector(0, 0, -50000))
        if actor:
            log(f"  Spawned test actor {actor.get_actor_label()}")
            for c in actor.get_components_by_class(unreal.ActorComponent):
                cls_name = c.get_class().get_name()
                if "Light" in cls_name or "Mesh" in cls_name or "Static" in cls_name:
                    log(
                        f"    spawned {c.get_name()} ({cls_name}) "
                        f"vis={safe_get(c,'visible')} intens={safe_get(c,'intensity')} "
                        f"hidden_in_game={safe_get(c,'hidden_in_game')}"
                    )
                    # materials
                    try:
                        n = c.get_num_materials()
                        for i in range(n):
                            log(f"      mat[{i}]={c.get_material(i)}")
                    except Exception:
                        pass
            actor.destroy_actor()
    except Exception as e:
        log(f"  spawn err: {e}")


def dump_scs_node(node, indent):
    try:
        name = node.get_name()
        cls = node.get_class().get_name()
        var = safe_get(node, "internal_variable_name")
        tmpl = safe_get(node, "component_template")
        log(f"{indent}SCSNode {name} ({cls}) var={var}")
        if tmpl is not None:
            log(
                f"{indent}  template {tmpl.get_class().get_name()} "
                f"vis={safe_get(tmpl,'visible')} intens={safe_get(tmpl,'intensity')} "
                f"affects={safe_get(tmpl,'affects_world')}"
            )
        # children
        children = safe_get(node, "child_nodes")
        if children:
            for ch in children:
                dump_scs_node(ch, indent + "  ")
    except Exception as e:
        log(f"{indent}node err {e}")


def main():
    # Ensure a map is loaded for spawning
    unreal.EditorLoadingAndSavingUtils.load_map("/Game/Office/Maps/Office")
    for p in BPS:
        dump_bp(p)
    log("Done")


if __name__ == "__main__":
    main()
