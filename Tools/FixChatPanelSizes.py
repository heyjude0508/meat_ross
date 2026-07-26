# Make WBP_ChatPanel Border and VerticalBox the same size:
# - clear Border + BorderSlot padding
# - size Border canvas slot to content (VerticalBox)
import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_ChatPanel"


def log(m):
    unreal.log(f"[ChatPanelFix] {m}")


def zero_margin():
    m = unreal.Margin()
    m.left = 0.0
    m.top = 0.0
    m.right = 0.0
    m.bottom = 0.0
    return m


def find_designer_widget(cls, name):
    """Prefer WidgetBlueprint designer tree over generated _C tree."""
    candidates = []
    for obj in unreal.ObjectIterator(cls):
        path = obj.get_path_name()
        if "WBP_ChatPanel" not in path:
            continue
        if obj.get_name() != name:
            continue
        candidates.append(obj)
    # Prefer non-_C path
    for obj in candidates:
        if ":WidgetTree." in obj.get_path_name() and "WBP_ChatPanel_C" not in obj.get_path_name():
            return obj
    return candidates[0] if candidates else None


def main():
    unreal.EditorAssetLibrary.load_asset(PATH)

    border = find_designer_widget(unreal.Border, "Border_20")
    vbox = find_designer_widget(unreal.VerticalBox, "VerticalBox_77")
    if not border or not vbox:
        log(f"ERROR border={border} vbox={vbox}")
        return

    log(f"border={border.get_path_name()}")
    log(f"vbox={vbox.get_path_name()}")

    # 1) Border content padding -> 0
    border.set_editor_property("padding", zero_margin())
    border.set_editor_property("horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_FILL)
    border.set_editor_property("vertical_alignment", unreal.VerticalAlignment.V_ALIGN_FILL)
    log("Set Border padding=0, align=FILL")

    # 2) BorderSlot around VerticalBox -> 0 padding, FILL
    slot = vbox.slot
    if isinstance(slot, unreal.BorderSlot):
        slot.set_editor_property("padding", zero_margin())
        slot.set_editor_property("horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_FILL)
        slot.set_editor_property("vertical_alignment", unreal.VerticalAlignment.V_ALIGN_FILL)
        log("Set BorderSlot padding=0, align=FILL")
    else:
        log(f"Unexpected vbox slot type: {type(slot)}")

    # 3) Canvas slot: size to content so Border matches VerticalBox desired size
    cslot = border.slot
    if isinstance(cslot, unreal.CanvasPanelSlot):
        before = cslot.get_size()
        log(f"Canvas size before={before}, auto_size={cslot.get_auto_size()}")
        try:
            cslot.set_auto_size(True)
            log("set_auto_size(True)")
        except Exception as e:
            log(f"set_auto_size failed: {e}")
            try:
                cslot.set_editor_property("b_auto_size", True)
            except Exception as e2:
                log(f"b_auto_size failed: {e2}")

        # Keep anchors centered; position can stay. With auto size, right/bottom become unused.
        # Optional: normalize alignment to center of anchor point
        try:
            cslot.set_alignment(unreal.Vector2D(0.5, 0.5))
            log("set_alignment center")
        except Exception as e:
            log(f"alignment: {e}")

        log(f"Canvas size after={cslot.get_size()}, auto_size={cslot.get_auto_size()}")
        log(f"layout after={cslot.get_layout()}")
    else:
        log(f"Unexpected border slot: {type(cslot)}")

    # Also ensure inner VerticalBox_586 fills parent
    inner = find_designer_widget(unreal.VerticalBox, "VerticalBox_586")
    if inner and isinstance(inner.slot, unreal.VerticalBoxSlot):
        inner.slot.set_editor_property("padding", zero_margin())
        inner.slot.set_editor_property("horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_FILL)
        inner.slot.set_editor_property("vertical_alignment", unreal.VerticalAlignment.V_ALIGN_FILL)
        # Fill parent instead of Automatic if we want stretch — keep Automatic for content height
        log("Normalized VerticalBox_586 slot padding/align")

    # Compile + save widget blueprint
    wbp = unreal.EditorAssetLibrary.load_asset(PATH)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(wbp)
        log("Compiled")
    except Exception as e:
        log(f"compile: {e}")
    unreal.EditorAssetLibrary.save_asset(PATH)
    log("Saved. Done.")


if __name__ == "__main__":
    main()
