import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat"

def log(m):
    unreal.log(f"[CDWire] {m}"); print(f"[CDWire] {m}")

def member(ref):
    try:
        return str(ref.member_name)
    except Exception:
        return str(ref)

bp = unreal.EditorAssetLibrary.load_asset(PATH)
log(f"loaded={bp}")

# variables
try:
    for v in bp.new_variables or []:
        log(f"VAR {v.var_name} type={v.var_type}")
except Exception as e:
    log(f"new_variables err={e}")

# all graphs via iterator
for g in unreal.ObjectIterator(unreal.EdGraph):
    path = g.get_path_name()
    if "/Game/SubwayTrain/UI_Blueprint/WBP_Chat." not in path:
        continue
    if "WBP_ChatMsg" in path:
        continue
    nodes = []
    try:
        nodes = list(g.nodes)
    except Exception:
        continue
    hits = []
    for n in nodes:
        blob = n.get_class().get_name() + "|" + n.get_name()
        for prop in ("custom_function_name", "member_name"):
            try:
                blob += "|" + str(n.get_editor_property(prop))
            except Exception:
                pass
        for prop in ("event_reference", "function_reference", "variable_reference"):
            try:
                ref = n.get_editor_property(prop)
                blob += "|" + prop + "=" + member(ref)
            except Exception:
                pass
        # class pin defaults for create widget
        try:
            for p in n.pins:
                try:
                    if p.default_object:
                        blob += "|pinObj=" + p.default_object.get_path_name()
                except Exception:
                    pass
                try:
                    if p.default_value and ("Countdown" in str(p.default_value) or "WBP_" in str(p.default_value)):
                        blob += "|pinVal=" + str(p.default_value)
                except Exception:
                    pass
        except Exception:
            pass
        low = blob.lower()
        if any(k in low for k in ("countdown", "viewport", "createwidget", "removefrom", "add_to_viewport", "addtoviewport")) or "K2Node_CreateWidget" in blob:
            hits.append((n, blob))
    if hits:
        log(f"==== {g.get_name()} ({len(nodes)} nodes) ====")
        for n, blob in hits:
            log(f"HIT {blob}")
            try:
                for p in n.pins:
                    links=[]
                    try:
                        for lp in p.linked_to:
                            links.append(f"{lp.get_owning_node().get_class().get_name()}:{lp.get_owning_node().get_name()}.{lp.get_name()}")
                    except Exception:
                        pass
                    dv=""; dobj=""
                    try: dv=p.default_value
                    except Exception: pass
                    try:
                        if p.default_object: dobj=p.default_object.get_path_name()
                    except Exception: pass
                    if links or dv or dobj or p.get_name() in ("execute","then","self","Class","ReturnValue","Target"):
                        log(f"  {p.get_name()} dv={dv!r} obj={dobj} -> {links}")
            except Exception as e:
                log(f"  pin err {e}")

# Also scan WBP_Countdown for Tick/Construct and whether it needs parent
for g in unreal.ObjectIterator(unreal.EdGraph):
    path = g.get_path_name()
    if "WBP_Countdown" not in path or "WBP_Countdown_C" in path:
        continue
    log(f"CDGRAPH {g.get_name()} nodes={len(list(g.nodes))}")
    for n in list(g.nodes):
        blob = n.get_class().get_name()
        for prop in ("custom_function_name",):
            try: blob += "|" + str(n.get_editor_property(prop))
            except Exception: pass
        for prop in ("event_reference", "function_reference"):
            try:
                ref = n.get_editor_property(prop)
                blob += "|" + member(ref)
            except Exception: pass
        log(f"  N {blob}")

log("DONE")
