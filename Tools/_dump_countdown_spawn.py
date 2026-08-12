import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat"

def log(m):
    unreal.log(f"[CDSpawn] {m}"); print(f"[CDSpawn] {m}")

def pin_info(pin):
    try:
        name = pin.get_name()
    except Exception:
        name = "?"
    links = []
    try:
        for lp in pin.linked_to:
            try:
                links.append(f"{lp.get_owning_node().get_name()}.{lp.get_name()}")
            except Exception:
                links.append("?")
    except Exception:
        pass
    dv = ""
    try:
        dv = pin.default_value
    except Exception:
        pass
    try:
        dobj = pin.default_object
        if dobj:
            dv = str(dobj.get_path_name())
    except Exception:
        pass
    return name, dv, links

def dump_node(n, tag=""):
    cls = n.get_class().get_name()
    name = n.get_name()
    extras = []
    for prop in ("custom_function_name", "b_override_function"):
        try:
            v = n.get_editor_property(prop)
            if v not in (None, "", False):
                extras.append(f"{prop}={v}")
        except Exception:
            pass
    for prop in ("event_reference", "function_reference", "variable_reference", "member_name"):
        try:
            ref = n.get_editor_property(prop)
            if ref is None:
                continue
            if hasattr(ref, "member_name"):
                extras.append(f"{prop}={ref.member_name}")
            else:
                extras.append(f"{prop}={ref}")
        except Exception:
            pass
    try:
        extras.append(f"pos=({n.node_pos_x},{n.node_pos_y})")
    except Exception:
        pass
    log(f"{tag}NODE {cls} {name} | {' | '.join(str(x) for x in extras)}")
    try:
        pins = list(n.pins)
    except Exception:
        pins = []
    for p in pins:
        pname, dv, links = pin_info(p)
        interesting = bool(links) or pname.lower() in ("then","execute","self","target","class","returnvalue","worldcontextobject","zorder") or (dv not in ("", None, "0", "0.0", "false", "True", "False") and "exec" not in pname.lower())
        if interesting:
            log(f"{tag}  PIN {pname} default={dv!r} -> {links}")

bp = unreal.EditorAssetLibrary.load_asset(PATH)
# vars
try:
    for v in unreal.BlueprintEditorLibrary.get_blueprint_variable_names(bp) or []:
        if "count" in str(v).lower() or "timer" in str(v).lower() or "chat" in str(v).lower():
            log(f"VAR {v}")
except Exception as e:
    log(f"vars err {e}")

graphs = []
for attr in ("ubergraph_pages", "function_graphs", "event_graphs"):
    try:
        for g in bp.get_editor_property(attr) or []:
            graphs.append(g)
    except Exception:
        pass
try:
    for g in unreal.BlueprintEditorLibrary.get_uber_graph_pages(bp) or []:
        graphs.append(g)
except Exception:
        pass

seen=set(); uniq=[]
for g in graphs:
    p=g.get_path_name()
    if p not in seen:
        seen.add(p); uniq.append(g)

keywords = ("countdown", "timer", "viewport", "create", "widget", "construct", "begin", "start", "add", "remove", "visible")
for g in uniq:
    log(f"==== GRAPH {g.get_name()} nodes={len(list(g.nodes))} ====")
    for n in list(g.nodes):
        blob = n.get_class().get_name() + " " + n.get_name()
        for prop in ("custom_function_name",):
            try:
                blob += " " + str(n.get_editor_property(prop))
            except Exception:
                pass
        for prop in ("event_reference", "function_reference", "variable_reference"):
            try:
                ref = n.get_editor_property(prop)
                if ref is not None and hasattr(ref, "member_name"):
                    blob += " " + str(ref.member_name)
            except Exception:
                pass
        low = blob.lower()
        if any(k in low for k in keywords) or "WBP_Countdown" in blob or "Countdown" in blob:
            dump_node(n)
            # also dump nearby linked nodes lightly
            try:
                for p in n.pins:
                    for lp in p.linked_to:
                        on = lp.get_owning_node()
                        dump_node(on, tag="  link.")
            except Exception:
                pass

log("DONE")
