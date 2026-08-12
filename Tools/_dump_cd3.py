import unreal, traceback

def log(m):
    unreal.log(f"[CD3] {m}"); print(f"[CD3] {m}")

def safe_pins(n):
    try:
        return list(n.pins)
    except Exception:
        return []

def dump(n, title=""):
    log(f"-- {title}{n.get_class().get_name()} {n.get_name()} --")
    for pin in safe_pins(n):
        try:
            links=[]
            for lp in pin.linked_to or []:
                on=lp.get_owning_node()
                links.append(f"{on.get_class().get_name()}:{on.get_name()}.{lp.get_name()}")
            dobj=""
            try:
                if pin.default_object:
                    dobj=pin.default_object.get_path_name()
            except Exception:
                pass
            dv=""
            try: dv=pin.default_value
            except Exception: pass
            if links or dobj or (dv not in (None,"","0","0.0","false","true","False","True")) or pin.get_name() in ("execute","then","self","Class","ReturnValue","Target","Owning Object"):
                log(f"  {pin.get_name()} dv={dv!r} obj={dobj} -> {links}")
        except Exception as e:
            log(f"  pinerr {e}")

unreal.EditorAssetLibrary.load_asset("/Game/SubwayTrain/UI_Blueprint/WBP_Chat")
unreal.EditorAssetLibrary.load_asset("/Game/SubwayTrain/UI_Blueprint/WBP_Countdown")

# Focus EventGraph + Start Chat + Check Answer + Construct
targets = (
    "/Game/SubwayTrain/UI_Blueprint/WBP_Chat.WBP_Chat:EventGraph",
    "/Game/SubwayTrain/UI_Blueprint/WBP_Chat.WBP_Chat:Start Chat",
    "/Game/SubwayTrain/UI_Blueprint/WBP_Chat.WBP_Chat:Construct",
    "/Game/SubwayTrain/UI_Blueprint/WBP_Chat.WBP_Chat:Check Answer And Finish",
    "/Game/SubwayTrain/UI_Blueprint/WBP_Chat.WBP_Chat:Submit Reply",
)

for g in unreal.ObjectIterator(unreal.EdGraph):
    p = g.get_path_name()
    if p not in targets:
        continue
    log(f"==== GRAPH {p} ====")
    for n in list(g.nodes):
        cls = n.get_class().get_name()
        interesting = cls in ("K2Node_CreateWidget","K2Node_Event","K2Node_CustomEvent","K2Node_VariableSet","K2Node_VariableGet","K2Node_CallFunction","K2Node_IfThenElse","K2Node_ExecutionSequence")
        name_hit = False
        blob = cls
        try:
            if cls == "K2Node_CallFunction":
                ref = n.get_editor_property("function_reference")
                mn = str(ref.member_name)
                blob += "|" + mn
                if mn in ("AddToViewport","RemoveFromParent","SetVisibility","CreateWidget") or "Countdown" in mn or "Viewport" in mn:
                    interesting = True; name_hit=True
            if cls in ("K2Node_VariableSet","K2Node_VariableGet"):
                ref = n.get_editor_property("variable_reference")
                mn = str(ref.member_name)
                blob += "|" + mn
                if "Countdown" in mn or "Timer" in mn:
                    interesting = True; name_hit=True
            if cls in ("K2Node_Event","K2Node_CustomEvent"):
                try:
                    ref = n.get_editor_property("event_reference")
                    blob += "|" + str(ref.member_name)
                except Exception:
                    pass
                try:
                    blob += "|cf=" + str(n.get_editor_property("custom_function_name"))
                except Exception:
                    pass
                interesting = True
            if cls == "K2Node_CreateWidget":
                interesting = True; name_hit=True
        except Exception:
            pass
        # also if any pin mentions countdown
        for pin in safe_pins(n):
            try:
                if pin.default_object and "Countdown" in pin.default_object.get_path_name():
                    interesting=True; name_hit=True
            except Exception:
                pass
        if interesting and (name_hit or cls in ("K2Node_Event","K2Node_CustomEvent","K2Node_CreateWidget") or "Countdown" in blob or "RemoveFromParent" in blob or "AddToViewport" in blob):
            dump(n, blob+" :: ")

# Search all K2 nodes under WBP_Chat for Countdown / RemoveFromParent / AddToViewport
log("==== GLOBAL SCAN ====")
for n in unreal.ObjectIterator(unreal.K2Node):
    p = n.get_path_name()
    if "WBP_Chat.WBP_Chat:" not in p or "WBP_ChatMsg" in p:
        continue
    cls = n.get_class().get_name()
    keep=False
    label=cls
    try:
        if cls == "K2Node_CallFunction":
            mn=str(n.get_editor_property("function_reference").member_name)
            label += "|"+mn
            if mn in ("AddToViewport","RemoveFromParent","SetVisibility"):
                keep=True
        if cls in ("K2Node_VariableSet","K2Node_VariableGet"):
            mn=str(n.get_editor_property("variable_reference").member_name)
            label += "|"+mn
            if "Countdown" in mn or "Timer" in mn:
                keep=True
        if cls == "K2Node_CreateWidget":
            for pin in safe_pins(n):
                try:
                    if pin.default_object and "Countdown" in pin.default_object.get_path_name():
                        keep=True
                except Exception:
                    pass
                try:
                    if pin.get_name()=="Class" and pin.default_value and "Countdown" in str(pin.default_value):
                        keep=True
                except Exception:
                    pass
    except Exception:
        pass
    if keep:
        dump(n, label+" @ "+p+" :: ")

log("DONE")
