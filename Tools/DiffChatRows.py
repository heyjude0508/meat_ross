"""Diff row A (SizeBox_66) against row B (SizeBox_127) in WBP_Chat, field by field."""
import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat"
PREFIX = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat.WBP_Chat:WidgetTree."


def log(m):
    unreal.log(f"[Diff] {m}")


def widgets():
    out = {}
    for obj in unreal.ObjectIterator(unreal.Widget):
        p = obj.get_path_name()
        if p.startswith(PREFIX):
            out[obj.get_name()] = obj
    return out


def rt_fields(w):
    rt = w.render_transform
    piv = w.render_transform_pivot
    return {
        "RT.Translation": (round(rt.translation.x, 3), round(rt.translation.y, 3)),
        "RT.Scale": (round(rt.scale.x, 4), round(rt.scale.y, 4)),
        "RT.Shear": (round(rt.shear.x, 3), round(rt.shear.y, 3)),
        "RT.Angle": round(rt.angle, 3),
        "RT.Pivot": (round(piv.x, 3), round(piv.y, 3)),
    }


def slot_fields(w):
    s = w.slot
    out = {"Slot.Class": s.get_class().get_name() if s else "None"}
    if not s:
        return out
    for p in ("horizontal_alignment", "vertical_alignment"):
        try:
            out[f"Slot.{p}"] = str(s.get_editor_property(p)).split(".")[-1].split(":")[0]
        except Exception:
            pass
    try:
        m = s.get_editor_property("padding")
        out["Slot.Padding"] = (m.left, m.top, m.right, m.bottom)
    except Exception:
        pass
    try:
        sz = s.get_editor_property("size")
        out["Slot.Size"] = (str(sz.size_rule).split(".")[-1].split(":")[0], sz.value)
    except Exception:
        pass
    return out


def widget_fields(w):
    f = {"Class": w.get_class().get_name(), "Visibility": str(w.get_editor_property("visibility")).split(".")[-1].split(":")[0]}
    f.update(rt_fields(w))
    f.update(slot_fields(w))
    if isinstance(w, unreal.SizeBox):
        for p in ("width_override", "height_override", "min_desired_width", "min_desired_height",
                  "max_desired_width", "max_desired_height", "min_aspect_ratio", "max_aspect_ratio"):
            try:
                f[f"SizeBox.{p}"] = round(float(w.get_editor_property(p)), 3)
            except Exception:
                pass
    if isinstance(w, unreal.Image):
        br = w.get_editor_property("brush")
        ro = br.get_editor_property("resource_object")
        f["Image.Resource"] = ro.get_name() if ro else None
        f["Image.DrawAs"] = str(br.get_editor_property("draw_as")).split(".")[-1].split(":")[0]
        try:
            m = br.get_editor_property("margin")
            f["Image.BrushMargin"] = (m.left, m.top, m.right, m.bottom)
        except Exception:
            pass
        try:
            t = br.get_editor_property("tint_color").get_editor_property("specified_color")
            f["Image.Tint"] = (round(t.r, 3), round(t.g, 3), round(t.b, 3), round(t.a, 3))
        except Exception:
            pass
        c = w.get_editor_property("color_and_opacity")
        f["Image.ColorAndOpacity"] = (round(c.r, 3), round(c.g, 3), round(c.b, 3), round(c.a, 3))
    if isinstance(w, unreal.RadialSlider):
        for p in ("value", "use_vertical_drag", "show_slider_handle", "show_slider_hand",
                  "slider_bar_color", "slider_handle_color", "slider_progress_color",
                  "center_background_color", "slider_range", "slider_handle_start_angle",
                  "slider_handle_end_angle", "angular_offset", "hand_start_angle", "hand_end_angle"):
            try:
                v = w.get_editor_property(p)
                if isinstance(v, unreal.LinearColor):
                    f[f"Radial.{p}"] = (round(v.r, 3), round(v.g, 3), round(v.b, 3), round(v.a, 3))
                else:
                    f[f"Radial.{p}"] = v if not isinstance(v, float) else round(v, 3)
            except Exception:
                pass
        try:
            st = w.get_editor_property("widget_style")
            f["Radial.BarThickness"] = round(st.get_editor_property("bar_thickness"), 3)
        except Exception:
            pass
    if isinstance(w, unreal.EditableTextBox):
        for p in ("hint_text", "is_read_only", "justification"):
            try:
                f[f"Text.{p}"] = str(w.get_editor_property(p))
            except Exception:
                pass
    return f


def compare(name_a, wa, name_b, wb):
    log(f"########## {name_a}  vs  {name_b} ##########")
    fa, fb = widget_fields(wa), widget_fields(wb)
    keys = sorted(set(fa) | set(fb))
    diffs = 0
    for k in keys:
        va, vb = fa.get(k, "<absent>"), fb.get(k, "<absent>")
        if va != vb:
            diffs += 1
            log(f"  DIFF {k}")
            log(f"       A={va}")
            log(f"       B={vb}")
    if diffs == 0:
        log("  identical")
    return diffs


def child_names(w):
    try:
        return [w.get_child_at(i).get_name() for i in range(w.get_children_count())]
    except Exception:
        return []


def main():
    unreal.EditorAssetLibrary.load_asset(PATH)
    w = widgets()
    log(f"all widgets: {sorted(w)}")

    # Locate B's slider wrapper (name is unknown if created by hand).
    ov_b = w.get("Overlay_166")
    box_b = None
    if ov_b:
        log(f"Overlay_90  children order: {child_names(w.get('Overlay_90'))}")
        log(f"Overlay_166 children order: {child_names(ov_b)}")
        for i in range(ov_b.get_children_count()):
            c = ov_b.get_child_at(i)
            if isinstance(c, unreal.SizeBox):
                box_b = c
    log(f"B slider wrapper SizeBox = {box_b.get_name() if box_b else 'NONE (structure differs!)'}")

    total = 0
    pairs = [
        ("SizeBox_66", "SizeBox_127"),
        ("HorizontalBox_40", "HorizontalBox_229"),
        ("Overlay_90", "Overlay_166"),
        ("RadialSliderA", "RadialSliderB"),
        ("ImageA", "ImageB"),
        ("TextBoxA", "TextBoxB"),
    ]
    for a, b in pairs:
        if a in w and b in w:
            total += compare(a, w[a], b, w[b])
        else:
            log(f"missing pair {a}/{b}")

    if box_b and "SizeBox_129" in w:
        total += compare("SizeBox_129", w["SizeBox_129"], box_b.get_name(), box_b)

    # Parent context that also affects both rows.
    vb = w.get("VerticalBox_586")
    if vb:
        log("########## VerticalBox_586 (shared parent) ##########")
        for k, v in widget_fields(vb).items():
            log(f"  {k}={v}")

    log(f"TOTAL DIFFS = {total}")


if __name__ == "__main__":
    main()
