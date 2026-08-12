import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_Countdown"
PREFIX = "/Game/SubwayTrain/UI_Blueprint/WBP_Countdown.WBP_Countdown:WidgetTree."

def log(m):
    unreal.log(f"[CDCheck] {m}"); print(f"[CDCheck] {m}")

def find(name):
    for obj in unreal.ObjectIterator(unreal.Widget):
        p = obj.get_path_name()
        if p.startswith(PREFIX) and "WBP_Countdown_C" not in p and obj.get_name() == name:
            return obj
    return None

unreal.EditorAssetLibrary.load_asset(PATH)
names = []
for obj in unreal.ObjectIterator(unreal.Widget):
    p = obj.get_path_name()
    if p.startswith(PREFIX) and "WBP_Countdown_C" not in p:
        names.append(f"{obj.get_name()}<{obj.get_class().get_name()}>")
log("tree=" + str(sorted(set(names))))

for name in ("CountdownValue", "ProgressBar_73", "CanvasPanel_18"):
    w = find(name)
    if not w:
        log(f"MISSING {name}")
        continue
    log(f"==== {name} ({w.get_class().get_name()}) ====")
    try:
        log(f"  visibility={w.get_editor_property('visibility')}")
    except Exception:
        pass
    try:
        rt = w.get_editor_property("render_transform")
        log(f"  RT.t={rt.translation} s={rt.scale} a={rt.angle}")
    except Exception as e:
        log(f"  RT err={e}")
    if w.get_class().get_name() == "TextBlock":
        for p in ("text", "justification", "min_desired_width", "auto_wrap_text"):
            try:
                log(f"  {p}={w.get_editor_property(p)}")
            except Exception:
                pass
        try:
            font = w.get_editor_property("font")
            log(f"  font.size={font.size} typeface={getattr(font,'typeface_font_name',None)}")
        except Exception as e:
            log(f"  font err={e}")
        try:
            log(f"  color={w.get_editor_property('color_and_opacity')}")
        except Exception:
            pass
    if w.get_class().get_name() == "ProgressBar":
        for p in ("percent", "fill_color_and_opacity", "bar_fill_type", "bar_fill_style"):
            try:
                log(f"  {p}={w.get_editor_property(p)}")
            except Exception:
                pass
    slot = getattr(w, "slot", None)
    if isinstance(slot, unreal.CanvasPanelSlot):
        log(f"  anchors={slot.get_anchors()}")
        log(f"  alignment={slot.get_alignment()}")
        log(f"  position={slot.get_position()}")
        log(f"  size={slot.get_size()}")
        log(f"  auto_size={slot.get_auto_size()}")
        log(f"  z={slot.get_z_order()}")
        log(f"  layout={slot.get_layout()}")
    elif slot:
        log(f"  slotClass={slot.get_class().get_name()}")
log("DONE")
