# Fix WBP_Countdown HUD layout: top-center text + bar under it.
# Run with UnrealEditor-Cmd -ExecutePythonScript, or Output Log: py Tools/FixCountdownLayout.py
import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_Countdown"
PREFIX = "/Game/SubwayTrain/UI_Blueprint/WBP_Countdown.WBP_Countdown:WidgetTree."


def log(m):
    unreal.log(f"[FixCountdown] {m}")
    print(f"[FixCountdown] {m}")


def find(name):
    for obj in unreal.ObjectIterator(unreal.Widget):
        p = obj.get_path_name()
        if not p.startswith(PREFIX):
            continue
        if "WBP_Countdown_C" in p:
            continue
        if obj.get_name() == name:
            return obj
    return None


def set_top_center(slot, pos_x, pos_y, size_x, size_y, auto_size=False):
    anchors = unreal.Anchors()
    anchors.minimum = unreal.Vector2D(0.5, 0.0)
    anchors.maximum = unreal.Vector2D(0.5, 0.0)
    slot.set_anchors(anchors)
    slot.set_alignment(unreal.Vector2D(0.5, 0.0))
    slot.set_position(unreal.Vector2D(pos_x, pos_y))
    slot.set_size(unreal.Vector2D(size_x, size_y))
    try:
        slot.set_auto_size(auto_size)
    except Exception:
        try:
            slot.set_editor_property("b_auto_size", auto_size)
        except Exception as e:
            log(f"auto_size warn: {e}")


def main():
    unreal.EditorAssetLibrary.load_asset(PATH)

    text = find("CountdownValue")
    bar = find("ProgressBar_73")
    if not text or not bar:
        log(f"MISSING text={text} bar={bar}")
        return

    tslot = text.slot
    bslot = bar.slot
    if not isinstance(tslot, unreal.CanvasPanelSlot) or not isinstance(bslot, unreal.CanvasPanelSlot):
        log("Slots are not CanvasPanelSlot")
        return

    log(f"BEFORE text layout={tslot.get_layout()}")
    log(f"BEFORE bar  layout={bslot.get_layout()}")

    # Screen HUD: top center. Designer preview is 1280x720.
    set_top_center(tslot, 0.0, 48.0, 320.0, 56.0, auto_size=False)
    set_top_center(bslot, 0.0, 104.0, 280.0, 8.0, auto_size=False)

    try:
        text.set_editor_property("justification", unreal.TextJustify.CENTER)
    except Exception as e:
        log(f"justification: {e}")

    log(f"AFTER text layout={tslot.get_layout()}")
    log(f"AFTER bar  layout={bslot.get_layout()}")

    bp = unreal.EditorAssetLibrary.load_asset(PATH)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        log("Compiled")
    except Exception as e:
        log(f"compile: {e}")
    unreal.EditorAssetLibrary.save_asset(PATH)
    log("Saved. DONE")


if __name__ == "__main__":
    main()
