# Dump TextBoxB (reference) vs Border_162 + TextBoxA for visual match.
import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat"
PREFIX = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat.WBP_Chat:WidgetTree."


def log(m):
    unreal.log(f"[MatchAB] {m}")
    print(f"[MatchAB] {m}")


def find(name):
    hits = []
    for obj in unreal.ObjectIterator(unreal.Widget):
        p = obj.get_path_name()
        if not p.startswith(PREFIX):
            continue
        if "WBP_Chat_C" in p:
            continue
        if obj.get_name() == name:
            hits.append(obj)
    return hits[0] if hits else None


def dump(name):
    w = find(name)
    if not w:
        log(f"MISSING {name}")
        return None
    log(f"==== {name} ({w.get_class().get_name()}) path={w.get_path_name()}")
    for p in (
        "visibility",
        "render_opacity",
        "color_and_opacity",
        "text",
        "font",
        "auto_wrap_text",
        "wrap_text_at",
        "justification",
        "min_desired_width",
        "min_desired_height",
        "width_override",
        "height_override",
        "b_override_width_override",
        "b_override_height_override",
        "padding",
        "background_color",
        "foreground_color",
        "widget_style",
        "brush_color",
        "brush",
        "is_read_only",
        "hint_text",
    ):
        try:
            log(f"  {p}={w.get_editor_property(p)}")
        except Exception:
            pass
    try:
        rt = w.render_transform
        log(f"  RT scale={rt.scale} trans={rt.translation} angle={rt.angle}")
    except Exception:
        pass
    try:
        slot = w.slot
        if slot:
            log(f"  slot={slot.get_class().get_name()}")
            for p in (
                "padding",
                "horizontal_alignment",
                "vertical_alignment",
                "size",
                "b_auto_size",
            ):
                try:
                    log(f"  slot.{p}={slot.get_editor_property(p)}")
                except Exception:
                    pass
    except Exception as e:
        log(f"  slot err {e}")
    # parent chain
    try:
        outer = w.get_outer()
        log(f"  outer={outer.get_name() if outer else None}")
    except Exception:
        pass
    return w


def dump_children_around(name):
    # list siblings under same horizontal/vertical parent names of interest
    for obj in unreal.ObjectIterator(unreal.Widget):
        p = obj.get_path_name()
        if PREFIX not in p or "WBP_Chat_C" in p:
            continue
        n = obj.get_name()
        if any(k in n for k in ("TextBox", "Border_162", "SizeBox_66", "SizeBox_127", "Alphabet", "Overlay_90", "Overlay_166", "ImageA", "ImageB")):
            try:
                slot = obj.slot
                pad = getattr(slot, "padding", None) if slot else None
            except Exception:
                pad = None
            log(f"TREE {obj.get_class().get_name()} '{n}' outer={obj.get_outer().get_name() if obj.get_outer() else None}")


def main():
    unreal.EditorAssetLibrary.load_asset(PATH)
    dump_children_around("")
    for n in (
        "TextBoxA",
        "TextBoxB",
        "Border_162",
        "SizeBox_66",
        "SizeBox_127",
        "AlphabetA",
        "AlphabetB",
        "Overlay_90",
        "Overlay_166",
    ):
        dump(n)
    log("DONE")


if __name__ == "__main__":
    main()
