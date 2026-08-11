# Inspect / fix WBP_ChatMsg layout for phone chat:
# - larger Boss/Me avatar
# - taller green bubble with readable text
# - ensure Construct sets BossMsg from BossText
#
# Target UI width ~393 (iPhone logical points used by this project).

import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_ChatMsg"

# iPhone-ish chat row sizing (designer units inside WBP_Chat)
AVATAR = 56.0
BUBBLE_MIN_H = 56.0
BUBBLE_PAD = 12.0
MSG_FONT_SIZE = 22.0


def log(m):
    unreal.log(f"[ChatMsgLayout] {m}")
    print(f"[ChatMsgLayout] {m}")


def find_named(cls, name):
    hits = []
    for obj in unreal.ObjectIterator(cls):
        path = obj.get_path_name()
        if "WBP_ChatMsg" not in path:
            continue
        if "WBP_ChatMsg_C" in path:
            continue
        if obj.get_name() != name:
            continue
        hits.append(obj)
    return hits[0] if hits else None


def dump_widget(name):
    w = find_named(unreal.Widget, name)
    if not w:
        log(f"MISSING {name}")
        return None
    log(f"--- {name} {w.get_class().get_name()} ---")
    for p in (
        "visibility",
        "render_opacity",
        "slot",
        "brush",
        "color_and_opacity",
        "text",
        "font",
        "auto_wrap_text",
        "wrap_text_at",
        "min_desired_width",
        "min_desired_height",
        "width_override",
        "height_override",
        "min_desired_slot_width",
        "min_desired_slot_height",
    ):
        try:
            log(f"  {p}={w.get_editor_property(p)}")
        except Exception:
            pass
    try:
        rt = w.get_editor_property("render_transform")
        log(f"  RT.scale={rt.scale} RT.translation={rt.translation} RT.angle={rt.angle}")
    except Exception:
        pass
    try:
        slot = w.slot
        if slot:
            log(f"  slotClass={slot.get_class().get_name()}")
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
    return w


def set_sizebox(name, w=None, h=None):
    sb = find_named(unreal.SizeBox, name) or find_named(unreal.Widget, name)
    if not sb:
        log(f"no SizeBox {name}")
        return
    # May be SizeBox wrapping icon/bubble - or widget itself
    for prop, val in (
        ("width_override", w),
        ("height_override", h),
        ("min_desired_width", w),
        ("min_desired_height", h),
    ):
        if val is None:
            continue
        try:
            sb.set_editor_property(prop, float(val))
            # enable override flags when present
            flag = {
                "width_override": "width_override",
                "height_override": "height_override",
            }.get(prop)
            if prop == "width_override":
                try:
                    sb.set_editor_property("b_override_width_override", True)
                except Exception:
                    pass
            if prop == "height_override":
                try:
                    sb.set_editor_property("b_override_height_override", True)
                except Exception:
                    pass
            log(f"set {name}.{prop}={val}")
        except Exception as e:
            log(f"skip {name}.{prop}: {e}")


def set_image_size(name, size):
    img = find_named(unreal.Image, name) or find_named(unreal.Widget, name)
    if not img:
        log(f"no Image {name}")
        return
    try:
        brush = img.get_editor_property("brush")
        brush.set_editor_property("image_size", unreal.Vector2D(float(size), float(size)))
        img.set_editor_property("brush", brush)
        log(f"set {name} image_size={size}")
    except Exception as e:
        log(f"image size fail {name}: {e}")
    # Also wrap with SizeBox if parent is SizeBox-named differently - set desired on widget
    try:
        img.set_editor_property("brush_size", unreal.Vector2D(float(size), float(size)))
    except Exception:
        pass


def set_text_block_font(name, size):
    tb = find_named(unreal.TextBlock, name) or find_named(unreal.Widget, name)
    if not tb:
        log(f"no TextBlock {name}")
        return
    try:
        font = tb.get_editor_property("font")
        try:
            font.set_editor_property("size", float(size))
        except Exception:
            # SlateFontInfo may use nested typeface
            try:
                font.size = float(size)
            except Exception as e:
                log(f"font.size fail: {e}")
        tb.set_editor_property("font", font)
        log(f"set {name} font size={size}")
    except Exception as e:
        log(f"font fail {name}: {e}")
    try:
        tb.set_editor_property("auto_wrap_text", True)
    except Exception:
        pass
    # Ensure visible dark/light text - if nearly invisible, set white
    try:
        c = tb.get_editor_property("color_and_opacity")
        log(f"  {name} color={c}")
    except Exception:
        pass


def set_border_padding(name, pad):
    b = find_named(unreal.Border, name) or find_named(unreal.Widget, name)
    if not b:
        log(f"no Border {name}")
        return
    try:
        m = unreal.Margin()
        m.left = m.right = m.top = m.bottom = float(pad)
        b.set_editor_property("padding", m)
        log(f"set {name} padding={pad}")
    except Exception as e:
        log(f"padding fail {name}: {e}")


def ensure_row_visibility():
    boss_row = find_named(unreal.Widget, "BossRow")
    me_row = find_named(unreal.Widget, "MeRow")
    if boss_row:
        try:
            boss_row.set_editor_property("visibility", unreal.SlateVisibility.VISIBLE)
            log("BossRow -> Visible")
        except Exception as e:
            log(f"BossRow vis: {e}")
    if me_row:
        try:
            # default collapsed for boss-only messages; Construct should toggle
            me_row.set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
            log("MeRow -> Collapsed (default)")
        except Exception as e:
            log(f"MeRow vis: {e}")


def inspect_construct_graph(bp):
    graphs = []
    try:
        for g in unreal.BlueprintEditorLibrary.get_uber_graph_pages(bp) or []:
            graphs.append(g)
    except Exception:
        pass
    try:
        for g in bp.get_editor_property("ubergraph_pages") or []:
            graphs.append(g)
    except Exception:
        pass
    for g in graphs:
        try:
            nodes = list(g.nodes)
        except Exception:
            continue
        log(f"graph {g.get_name()} nodes={len(nodes)}")
        for n in nodes:
            cls = n.get_class().get_name()
            extra = ""
            try:
                fr = n.get_editor_property("function_reference")
                extra += f" fn={getattr(fr, 'member_name', fr)}"
            except Exception:
                pass
            try:
                er = n.get_editor_property("event_reference")
                extra += f" ev={getattr(er, 'member_name', er)}"
            except Exception:
                pass
            try:
                extra += f" custom={n.get_editor_property('custom_function_name')}"
            except Exception:
                pass
            log(f"  {cls} {n.get_name()}{extra}")


def main():
    bp = unreal.EditorAssetLibrary.load_asset(PATH)
    if not bp:
        log("FAILED load")
        return
    log("=== INSPECT ===")
    for name in (
        "BossRow",
        "MeRow",
        "BossIcon",
        "MeIcon",
        "BossBubble",
        "Mebubble",
        "BossMsg",
        "MeMsg",
        "HorizontalBox_105",
        "SizeBox",
    ):
        dump_widget(name)

    # Also dump any SizeBox_* 
    for obj in unreal.ObjectIterator(unreal.SizeBox):
        path = obj.get_path_name()
        if "WBP_ChatMsg:WidgetTree" in path and "WBP_ChatMsg_C" not in path:
            log(f"SizeBox found: {obj.get_name()}")
            dump_widget(obj.get_name())

    inspect_construct_graph(bp)

    log("=== FIX SIZES ===")
    # Avatars
    set_image_size("BossIcon", AVATAR)
    set_image_size("MeIcon", AVATAR)
    # If icons sit in SizeBoxes named same parent - search SizeBoxes containing icon
    for obj in unreal.ObjectIterator(unreal.SizeBox):
        path = obj.get_path_name()
        if "WBP_ChatMsg:WidgetTree" not in path or "WBP_ChatMsg_C" in path:
            continue
        name = obj.get_name()
        # Heuristic: small sizeboxes near icons - set both avatar and bubble mins
        try:
            wo = obj.get_editor_property("width_override")
            ho = obj.get_editor_property("height_override")
        except Exception:
            wo = ho = None
        log(f"SizeBox {name} before w={wo} h={ho}")

    # Bubbles: padding + text
    set_border_padding("BossBubble", BUBBLE_PAD)
    set_border_padding("Mebubble", BUBBLE_PAD)
    set_text_block_font("BossMsg", MSG_FONT_SIZE)
    set_text_block_font("MeMsg", MSG_FONT_SIZE)

    # Force min height on bubble borders via slot / wrap
    for bname in ("BossBubble", "Mebubble"):
        b = find_named(unreal.Widget, bname)
        if not b:
            continue
        try:
            # min desired on border if available
            b.set_editor_property("min_desired_height", float(BUBBLE_MIN_H))
        except Exception:
            pass
        try:
            slot = b.slot
            if slot:
                try:
                    pad = unreal.Margin()
                    pad.left = pad.right = 8.0
                    pad.top = pad.bottom = 4.0
                    slot.set_editor_property("padding", pad)
                except Exception:
                    pass
                try:
                    slot.set_editor_property(
                        "horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_FILL
                    )
                except Exception:
                    pass
                try:
                    slot.set_editor_property(
                        "vertical_alignment", unreal.VerticalAlignment.V_ALIGN_CENTER
                    )
                except Exception:
                    pass
        except Exception:
            pass

    # Root horizontal boxes should fill width
    for hname in ("BossRow", "MeRow", "HorizontalBox_105"):
        h = find_named(unreal.Widget, hname)
        if not h:
            continue
        try:
            slot = h.slot
            if slot:
                try:
                    size = slot.get_editor_property("size")
                    # VerticalBox slot SizeRule Fill
                    size.set_editor_property("size_rule", unreal.SlateSizeRule.FILL)
                    slot.set_editor_property("size", size)
                    log(f"{hname} slot size FILL")
                except Exception as e:
                    log(f"{hname} slot size: {e}")
        except Exception:
            pass

    ensure_row_visibility()

    # Reset weird render scales to 1
    for name in ("BossRow", "MeRow", "BossIcon", "MeIcon", "BossBubble", "Mebubble", "BossMsg", "MeMsg"):
        w = find_named(unreal.Widget, name)
        if not w:
            continue
        try:
            rt = w.get_editor_property("render_transform")
            sc = rt.scale
            if abs(sc.x - 1.0) > 0.01 or abs(sc.y - 1.0) > 0.01:
                rt.set_editor_property("scale", unreal.Vector2D(1.0, 1.0))
                w.set_editor_property("render_transform", rt)
                log(f"reset scale {name} from {sc}")
        except Exception:
            pass

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as e:
        log(f"compile: {e}")
    unreal.EditorAssetLibrary.save_asset(PATH)
    log("=== DONE — check Construct still does SetText(BossMsg, BossText) ===")
    log("If text still empty: Event Construct -> SetText on BossMsg using BossText variable")


if __name__ == "__main__":
    main()
