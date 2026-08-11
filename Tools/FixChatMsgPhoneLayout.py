# Fix WBP_ChatMsg phone layout:
# 1) Wrap/force avatar SizeBox 56x56
# 2) Bubble padding + font + ensure text color visible on green
# 3) Report whether Construct SetText exists (manual fix if missing)
import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_ChatMsg"
AVATAR = 56.0
FONT_SIZE = 22.0
PAD = 12.0


def log(m):
    unreal.log(f"[FixChatMsg] {m}")
    print(f"[FixChatMsg] {m}")


def find(name):
    for obj in unreal.ObjectIterator(unreal.Widget):
        p = obj.get_path_name()
        if f"WBP_ChatMsg:WidgetTree.{name}" in p and "WBP_ChatMsg_C" not in p:
            return obj
    return None


def set_sizebox_fixed(sb, w, h):
    if not sb:
        return
    for flag, prop, val in (
        ("b_override_width_override", "width_override", w),
        ("b_override_height_override", "height_override", h),
    ):
        try:
            sb.set_editor_property(flag, True)
        except Exception:
            pass
        try:
            sb.set_editor_property(prop, float(val))
            log(f"{sb.get_name()}.{prop}={val}")
        except Exception as e:
            log(f"{sb.get_name()}.{prop} fail: {e}")


def set_image_size_ue57(img, size):
    """UE5.7 SlateBrush.ImageSize is DeprecateSlateVector2D."""
    if not img:
        return
    brush = img.get_editor_property("brush")
    try:
        # Preferred: set via helper if exists
        if hasattr(brush, "set_image_size"):
            brush.set_image_size(unreal.Vector2D(size, size))
        else:
            # Construct DeprecateSlateVector2D-like via two floats on struct copy
            sz = brush.get_editor_property("image_size")
            # try attributes X/Y or x/y
            for a, v in (("x", size), ("y", size), ("X", size), ("Y", size)):
                try:
                    setattr(sz, a, float(v))
                except Exception:
                    try:
                        sz.set_editor_property(a, float(v))
                    except Exception:
                        pass
            try:
                brush.set_editor_property("image_size", sz)
            except Exception as e:
                log(f"set image_size struct failed: {e}")
                # Fallback: replace whole brush resource size via SetBrushFromAtlas etc — skip
        img.set_editor_property("brush", brush)
        log(f"{img.get_name()} brush size attempt done")
    except Exception as e:
        log(f"image size {img.get_name()}: {e}")


def set_font(tb, size):
    if not tb:
        return
    font = tb.get_editor_property("font")
    try:
        font.set_editor_property("size", float(size))
    except Exception:
        try:
            font.size = float(size)
        except Exception as e:
            log(f"font size: {e}")
    tb.set_editor_property("font", font)
    try:
        tb.set_editor_property("auto_wrap_text", True)
    except Exception:
        pass
    # Black text on green bubble is OK; ensure alpha 1
    try:
        c = unreal.SlateColor()
        c.set_editor_property(
            "specified_color", unreal.LinearColor(0.05, 0.05, 0.05, 1.0)
        )
        try:
            c.set_editor_property("color_use_rule", unreal.SlateColorStylingMode.USE_COLOR_SPECIFIED)
        except Exception:
            pass
        tb.set_editor_property("color_and_opacity", c)
    except Exception as e:
        log(f"color: {e}")
    log(f"{tb.get_name()} font={size}")


def set_padding(border, pad):
    if not border:
        return
    m = unreal.Margin()
    m.left = m.right = m.top = m.bottom = float(pad)
    border.set_editor_property("padding", m)
    log(f"{border.get_name()} padding={pad}")


def dump_construct(bp):
    has_set_text = False
    pages = []
    try:
        pages = list(unreal.BlueprintEditorLibrary.get_uber_graph_pages(bp) or [])
    except Exception:
        pass
    if not pages:
        try:
            pages = list(bp.get_editor_property("ubergraph_pages") or [])
        except Exception:
            pages = []
    for g in pages:
        try:
            nodes = list(g.nodes)
        except Exception:
            continue
        log(f"EventGraph nodes={len(nodes)}")
        for n in nodes:
            blob = n.get_class().get_name() + " " + n.get_name()
            try:
                fr = n.get_editor_property("function_reference")
                blob += f" fn={fr.member_name}"
                if str(fr.member_name) in ("SetText", "SetText"):
                    has_set_text = True
            except Exception:
                pass
            try:
                er = n.get_editor_property("event_reference")
                blob += f" ev={er.member_name}"
            except Exception:
                pass
            log(f"  {blob}")
    return has_set_text


def main():
    bp = unreal.EditorAssetLibrary.load_asset(PATH)
    if not bp:
        log("load failed")
        return

    has_set_text = dump_construct(bp)
    log(f"Construct has SetText node: {has_set_text}")

    boss_icon = find("BossIcon")
    me_icon = find("MeIcon")
    set_image_size_ue57(boss_icon, AVATAR)
    set_image_size_ue57(me_icon, AVATAR)

    # BossRow/MeRow are SizeBoxes — set min height for row; width fill comes from parent
    boss_row = find("BossRow")
    me_row = find("MeRow")
    # Don't lock full row width; set min height so empty-ish rows still readable
    for row in (boss_row, me_row):
        if not row:
            continue
        try:
            row.set_editor_property("b_override_min_desired_height", True)
        except Exception:
            pass
        try:
            row.set_editor_property("min_desired_height", float(AVATAR + 8))
            log(f"{row.get_name()} min_desired_height={AVATAR+8}")
        except Exception as e:
            log(f"row min h: {e}")

    # If icons are direct children, try put fixed size on a parent SizeBox via slot padding
    # Create dedicated size by overriding on Icon's slot size if HorizontalBoxSlot has size
    for icon in (boss_icon, me_icon):
        if not icon:
            continue
        try:
            slot = icon.slot
            # HorizontalBoxSlot: don't fill — auto size
            slot.set_editor_property(
                "horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_CENTER
            )
            slot.set_editor_property(
                "vertical_alignment", unreal.VerticalAlignment.V_ALIGN_TOP
            )
            pad = unreal.Margin()
            pad.right = 10.0
            pad.left = pad.top = pad.bottom = 0.0
            slot.set_editor_property("padding", pad)
            size = slot.get_editor_property("size")
            size.set_editor_property("size_rule", unreal.SlateSizeRule.AUTOMATIC)
            slot.set_editor_property("size", size)
            log(f"{icon.get_name()} slot padded")
        except Exception as e:
            log(f"icon slot: {e}")

    # Force icon desired size via wrapping SizeBox if icon outer is SizeBox — else set render scale as last resort
    # Render scale fallback (designer units): if brush can't change, scale visual
    for icon in (boss_icon, me_icon):
        if not icon:
            continue
        try:
            brush = icon.get_editor_property("brush")
            sz = brush.get_editor_property("image_size")
            # read current
            cur = None
            for a in ("x", "X"):
                try:
                    cur = float(getattr(sz, a))
                    break
                except Exception:
                    pass
            log(f"{icon.get_name()} current image size x~{cur}")
            if cur is not None and cur > 1.0:
                scale = AVATAR / cur
                if abs(scale - 1.0) > 0.05:
                    rt = icon.get_editor_property("render_transform")
                    rt.set_editor_property("scale", unreal.Vector2D(scale, scale))
                    icon.set_editor_property("render_transform", rt)
                    icon.set_editor_property(
                        "render_transform_pivot", unreal.Vector2D(0.5, 0.5)
                    )
                    log(f"{icon.get_name()} render scale -> {scale:.3f} (from {cur})")
            else:
                # unknown size: apply absolute scale assuming ~32 default
                rt = icon.get_editor_property("render_transform")
                rt.set_editor_property("scale", unreal.Vector2D(AVATAR / 32.0, AVATAR / 32.0))
                icon.set_editor_property("render_transform", rt)
                log(f"{icon.get_name()} render scale fallback {AVATAR/32.0:.3f}")
        except Exception as e:
            log(f"scale fallback: {e}")

    set_padding(find("BossBubble"), PAD)
    set_padding(find("Mebubble"), PAD)
    set_font(find("BossMsg"), FONT_SIZE)
    set_font(find("MeMsg"), FONT_SIZE)

    # Bubble should fill remaining width
    for bname in ("BossBubble", "Mebubble"):
        b = find(bname)
        if not b:
            continue
        try:
            slot = b.slot
            size = slot.get_editor_property("size")
            size.set_editor_property("size_rule", unreal.SlateSizeRule.FILL)
            size.set_editor_property("value", 1.0)
            slot.set_editor_property("size", size)
            slot.set_editor_property(
                "horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_FILL
            )
            slot.set_editor_property(
                "vertical_alignment", unreal.VerticalAlignment.V_ALIGN_CENTER
            )
            log(f"{bname} Fill")
        except Exception as e:
            log(f"{bname} slot: {e}")

    # Visibility defaults
    try:
        find("BossRow").set_editor_property("visibility", unreal.SlateVisibility.VISIBLE)
        find("MeRow").set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
    except Exception:
        pass

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as e:
        log(f"compile {e}")
    unreal.EditorAssetLibrary.save_asset(PATH)

    if not has_set_text:
        log("ACTION REQUIRED: In WBP_ChatMsg Event Graph, wire:")
        log("  Event Construct -> SetText (target BossMsg, text = BossText variable)")
        log("  Also optional: SetText MeMsg from MeText; collapse empty row")
    else:
        log("SetText exists in graph — verify BossMsg target + BossText source")
    log("DONE")


if __name__ == "__main__":
    main()
