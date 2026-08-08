"""Dump PulseA / PulseB tracks and compare against the widgets' idle RenderTransform."""
import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat"
PREFIX = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat.WBP_Chat:WidgetTree."


def log(m):
    unreal.log(f"[Anim] {m}")


def main():
    unreal.EditorAssetLibrary.load_asset(PATH)

    idle = {}
    for obj in unreal.ObjectIterator(unreal.Widget):
        p = obj.get_path_name()
        if p.startswith(PREFIX):
            rt = obj.render_transform
            idle[obj.get_name()] = (
                (round(rt.translation.x, 3), round(rt.translation.y, 3)),
                (round(rt.scale.x, 4), round(rt.scale.y, 4)),
            )

    anims = []
    for obj in unreal.ObjectIterator(unreal.WidgetAnimation):
        p = obj.get_path_name()
        if "/Game/SubwayTrain/UI_Blueprint/WBP_Chat." not in p:
            continue
        if p.endswith("_INST") or "_INST" in obj.get_name():
            continue
        anims.append(obj)

    for a in sorted(anims, key=lambda x: x.get_name()):
        log(f"===== {a.get_name()} =====")
        rate = a.get_display_rate()
        log(f"  display_rate={rate.numerator}/{rate.denominator} "
            f"playback={a.get_playback_start()}..{a.get_playback_end()}")
        bindings = a.get_bindings()
        if not bindings:
            log("  (no bindings)")
        for b in bindings:
            name = str(b.get_display_name())
            log(f"  -- Binding '{name}'  idle RT = {idle.get(name, 'unknown')}")
            tracks = b.get_tracks()
            if not tracks:
                log("     (no tracks -> this widget is never animated)")
            for t in tracks:
                log(f"     Track {t.get_class().get_name()} property={t.get_property_name()}")
                for sec in t.get_sections():
                    log(f"       Section {sec.get_start_frame()} -> {sec.get_end_frame()}")
                    try:
                        for ch in sec.get_all_channels():
                            keys = ch.get_keys()
                            vals = []
                            for k in keys:
                                try:
                                    vals.append((k.get_time().frame_number.value, round(k.get_value(), 4)))
                                except Exception:
                                    vals.append(str(k))
                            if vals:
                                log(f"         {ch.get_name()}: {vals}")
                    except Exception as e:
                        log(f"         channel err {e}")

    log("===== Play Animation call sites =====")
    bp = unreal.EditorAssetLibrary.load_asset(PATH)
    try:
        for g in unreal.BlueprintEditorLibrary.get_blueprint_graphs(bp) if hasattr(unreal, "BlueprintEditorLibrary") else []:
            log(f"  graph {g.get_name()}")
    except Exception as e:
        log(f"  graph enumeration unavailable: {e}")


if __name__ == "__main__":
    main()
