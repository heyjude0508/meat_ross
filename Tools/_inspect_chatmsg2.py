import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_ChatMsg"

def log(m):
    unreal.log(f"[ChatMsg2] {m}"); print(f"[ChatMsg2] {m}")

def find(name):
    for obj in unreal.ObjectIterator(unreal.Widget):
        p = obj.get_path_name()
        if f"WBP_ChatMsg:WidgetTree.{name}" in p and "WBP_ChatMsg_C" not in p:
            return obj
    return None

bp = unreal.EditorAssetLibrary.load_asset(PATH)
# Construct graph nodes
for g in (unreal.BlueprintEditorLibrary.get_uber_graph_pages(bp) or []):
    log(f"GRAPH {g.get_name()}")
    for n in list(g.nodes):
        cls = n.get_class().get_name()
        info = cls + " " + n.get_name()
        for prop in ("custom_function_name",):
            try: info += f" {prop}={n.get_editor_property(prop)}"
            except: pass
        for prop in ("event_reference","function_reference","variable_reference"):
            try:
                ref = n.get_editor_property(prop)
                info += f" {prop}.member={getattr(ref,'member_name',None)}"
            except: pass
        log(info)
        try:
            for pin in n.pins:
                links=[f"{lp.get_owning_node().get_name()}.{lp.get_name()}" for lp in (pin.linked_to or [])]
                if links or pin.get_name() in ("execute","then","self","Text","InText","BossText","Boss Msg","BossMsg"):
                    log(f"  pin {pin.get_name()} -> {links} default={pin.default_value!r}")
        except Exception as e:
            log(f"  pins err {e}")

for name in ("BossIcon","MeIcon","BossMsg","BossBubble"):
    w = find(name)
    if not w: log(f"missing {name}"); continue
    log(f"== {name} {w.get_class().get_name()}")
    if name.endswith("Icon"):
        try:
            brush = w.get_editor_property("brush")
            log(f" brush.image_size={brush.image_size} type={type(brush.image_size)}")
            log(f" brush dir={[x for x in dir(brush) if not x.startswith('_')][:40]}")
            # try DeprecateSlateVector2D
            try:
                sz = brush.get_editor_property("image_size")
                log(f" image_size raw={sz} dir={dir(sz)[:20]}")
            except Exception as e:
                log(f" get image_size {e}")
        except Exception as e:
            log(f"brush {e}")
    if name=="BossMsg":
        try: log(f" text={w.get_editor_property('text')}")
        except Exception as e: log(f"text {e}")
        try: log(f" font={w.get_editor_property('font')}")
        except Exception as e: log(f"font {e}")

# Variables
try:
    for v in unreal.BlueprintEditorLibrary.get_blueprint_variable_names(bp) or []:
        log(f"VAR {v}")
except Exception as e:
    log(f"vars {e}")
