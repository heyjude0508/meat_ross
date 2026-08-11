# Dump WBP_Chat EventGraph / functions / variables for analysis.
import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat"


def log(m):
    unreal.log(f"[DumpWBPChat] {m}")
    print(f"[DumpWBPChat] {m}")


def pin_brief(pin):
    try:
        name = pin.get_name()
    except Exception:
        name = "?"
    try:
        direction = str(pin.direction)
    except Exception:
        direction = "?"
    links = []
    try:
        for lp in pin.linked_to:
            try:
                links.append(f"{lp.get_owning_node().get_name()}.{lp.get_name()}")
            except Exception:
                links.append("?")
    except Exception:
        pass
    default = ""
    try:
        default = pin.default_value
    except Exception:
        pass
    return f"{name}({direction}) default={default!r} -> {links}"


def dump_node(n):
    cls = n.get_class().get_name()
    name = n.get_name()
    extra = []
    for prop in (
        "custom_function_name",
        "event_reference",
        "function_reference",
        "variable_reference",
        "delegate_reference",
        "member_name",
        "b_override_function",
        "b_internal_event",
        "timeline_name",
        "input_key",
    ):
        try:
            val = n.get_editor_property(prop)
            if val is not None:
                extra.append(f"{prop}={val}")
        except Exception:
            pass
    # Member names nested
    for prop in ("event_reference", "function_reference", "variable_reference"):
        try:
            ref = n.get_editor_property(prop)
            try:
                extra.append(f"{prop}.member_name={ref.member_name}")
            except Exception:
                pass
            try:
                extra.append(f"{prop}.member_parent={ref.member_parent}")
            except Exception:
                pass
        except Exception:
            pass
    try:
        extra.append(f"pos=({n.node_pos_x},{n.node_pos_y})")
    except Exception:
        pass
    log(f"NODE {cls} '{name}' {' | '.join(extra)}")
    try:
        pins = n.pins
    except Exception:
        try:
            pins = n.get_editor_property("pins")
        except Exception:
            pins = []
    for p in pins or []:
        log(f"  PIN {pin_brief(p)}")


def get_graphs(bp):
    graphs = []
    try:
        pages = unreal.BlueprintEditorLibrary.get_uber_graph_pages(bp)
        for g in pages or []:
            graphs.append(("uber", g))
    except Exception as e:
        log(f"uber pages: {e}")
    for attr in ("function_graphs", "macro_graphs", "event_graphs", "ubergraph_pages"):
        try:
            arr = bp.get_editor_property(attr)
            for g in arr or []:
                graphs.append((attr, g))
        except Exception:
            pass
    # ObjectIterator fallback
    try:
        for g in unreal.ObjectIterator(unreal.EdGraph):
            path = g.get_path_name()
            if "WBP_Chat" in path and "WBP_ChatMsg" not in path:
                graphs.append(("iter", g))
    except Exception as e:
        log(f"iter graphs: {e}")
    # unique by path
    seen = set()
    out = []
    for kind, g in graphs:
        if not g:
            continue
        p = g.get_path_name()
        if p in seen:
            continue
        seen.add(p)
        out.append((kind, g))
    return out


def dump_vars(bp):
    try:
        for v in bp.new_variables or []:
            try:
                log(f"VAR {v.var_name} type={v.var_type} default={getattr(v, 'default_value', None)}")
            except Exception:
                log(f"VAR {v}")
    except Exception as e:
        log(f"vars via new_variables: {e}")
    try:
        for v in unreal.BlueprintEditorLibrary.get_blueprint_variable_names(bp) or []:
            log(f"VARNAME {v}")
    except Exception as e:
        log(f"var names: {e}")


def main():
    bp = unreal.EditorAssetLibrary.load_asset(PATH)
    if not bp:
        log("FAILED load")
        return
    log(f"loaded {bp} class={bp.get_class().get_name()}")
    dump_vars(bp)
    graphs = get_graphs(bp)
    log(f"graph count={len(graphs)}")
    for kind, g in graphs:
        log(f"==== GRAPH kind={kind} name={g.get_name()} path={g.get_path_name()} ====")
        try:
            nodes = list(g.nodes)
        except Exception:
            try:
                nodes = list(g.get_editor_property("nodes"))
            except Exception:
                nodes = []
        log(f"node count={len(nodes)}")
        # sort by x
        def xpos(n):
            try:
                return int(n.node_pos_x)
            except Exception:
                return 0
        for n in sorted(nodes, key=xpos):
            dump_node(n)
    log("DONE")


if __name__ == "__main__":
    main()
