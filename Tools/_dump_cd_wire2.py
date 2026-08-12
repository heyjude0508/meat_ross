import unreal, traceback

def log(m):
    unreal.log(f"[CDWire2] {m}"); print(f"[CDWire2] {m}")

try:
    bp = unreal.EditorAssetLibrary.load_asset("/Game/SubwayTrain/UI_Blueprint/WBP_Chat")
    log(f"bp={bp}")
    graphs = []
    try:
        for g in unreal.BlueprintEditorLibrary.get_uber_graph_pages(bp) or []:
            graphs.append(g)
            log(f"uber {g.get_name()}")
    except Exception as e:
        log(f"uber err {e}")
    # Generated class ubergraph
    try:
        gc = bp.generated_class
        log(f"gen={gc}")
    except Exception as e:
        log(f"gen err {e}")

    # Find all objects with Countdown in path under WBP_Chat package
    count = 0
    for obj in unreal.ObjectIterator(unreal.Object):
        try:
            p = obj.get_path_name()
        except Exception:
            continue
        if "WBP_Chat" not in p or "WBP_ChatMsg" in p:
            continue
        name = obj.get_name()
        cls = obj.get_class().get_name()
        if "Countdown" in name or "Countdown" in cls or "CreateWidget" in cls or cls == "EdGraph":
            log(f"OBJ {cls} {name} :: {p}")
            count += 1
            if count > 80:
                break
    log(f"listed={count}")

    # Direct node search by class
    for cls_name in ("K2Node_CreateWidget", "K2Node_CallFunction", "K2Node_VariableSet", "K2Node_VariableGet", "K2Node_CustomEvent", "K2Node_Event"):
        cls = getattr(unreal, cls_name, None)
        if cls is None:
            # try finding via iterator filter
            pass
    create_nodes = []
    for obj in unreal.ObjectIterator(unreal.K2Node):
        p = obj.get_path_name()
        if "WBP_Chat." not in p or "WBP_ChatMsg" in p:
            continue
        c = obj.get_class().get_name()
        if c in ("K2Node_CreateWidget",) or "Countdown" in obj.get_name():
            create_nodes.append(obj)
            log(f"K2 {c} {obj.get_name()} {p}")
        # call function RemoveFromParent / AddToViewport
        if c == "K2Node_CallFunction":
            try:
                ref = obj.get_editor_property("function_reference")
                mn = str(ref.member_name)
                if mn in ("AddToViewport", "RemoveFromParent", "CreateWidget", "SetVisibility") or "Countdown" in mn:
                    log(f"CALL {mn} node={obj.get_name()} path={p}")
                    for pin in obj.pins:
                        links=[f"{lp.get_owning_node().get_name()}.{lp.get_name()}" for lp in (pin.linked_to or [])]
                        dv=getattr(pin,'default_value',None)
                        if links or (dv not in (None,"",)):
                            log(f"  pin {pin.get_name()} dv={dv!r} -> {links}")
            except Exception:
                pass
        if c == "K2Node_CreateWidget":
            log(f"CREATE {obj.get_name()} {p}")
            for pin in obj.pins:
                links=[f"{lp.get_owning_node().get_name()}.{lp.get_name()}" for lp in (pin.linked_to or [])]
                dobj=""
                try:
                    if pin.default_object: dobj=pin.default_object.get_path_name()
                except Exception:
                    pass
                dv=getattr(pin,'default_value',None)
                log(f"  pin {pin.get_name()} dv={dv!r} obj={dobj} -> {links}")
        if c in ("K2Node_VariableSet", "K2Node_VariableGet"):
            try:
                ref = obj.get_editor_property("variable_reference")
                mn = str(ref.member_name)
                if "Countdown" in mn or "Timer" in mn:
                    log(f"VARNODE {c} {mn} {p}")
                    for pin in obj.pins:
                        links=[f"{lp.get_owning_node().get_name()}.{lp.get_name()}" for lp in (pin.linked_to or [])]
                        if links or pin.get_name() in ("execute","then","CountdownTimer","Countdown Timer"):
                            log(f"  pin {pin.get_name()} -> {links}")
            except Exception:
                pass
    log("DONE")
except Exception:
    log(traceback.format_exc())
