"""Dump PulseA / PulseB bindings and transform keys, plus the idle RenderTransform
of the widgets they animate, so drift can be spotted directly."""
import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat"
PREFIX = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat.WBP_Chat:WidgetTree."


def log(m):
    unreal.log(f"[Pulse] {m}")


def idle_transforms():
    out = {}
    for obj in unreal.ObjectIterator(unreal.Widget):
        p = obj.get_path_name()
        if p.startswith(PREFIX):
            rt = obj.render_transform
            out[obj.get_name()] = (
                (round(rt.translation.x, 3), round(rt.translation.y, 3)),
                (round(rt.scale.x, 4), round(rt.scale.y, 4)),
            )
    return out


def main():
    unreal.EditorAssetLibrary.load_asset(PATH)
    idle = idle_transforms()

    anims = []
    for obj in unreal.ObjectIterator(unreal.WidgetAnimation):
        p = obj.get_path_name()
        if "/Game/SubwayTrain/UI_Blueprint/WBP_Chat." not in p:
            continue
        if p.endswith("_INST"):
            continue
        anims.append(obj)

    for a in sorted(anims, key=lambda x: x.get_name()):
        if a.get_name().endswith("_INST"):
            continue
        log(f"===== {a.get_name()} =====")
        try:
            log(f"  rate={a.get_display_rate().numerator}/{a.get_display_rate().denominator} "
                f"range={a.get_playback_start()}..{a.get_playback_end()}")
        except Exception:
            pass
        bindings = a.get_bindings()
        if not bindings:
            log("  (no bindings)")
        for b in bindings:
            name = b.get_display_name()
            log(f"  -- binds '{name}'  idle RT: T={idle.get(name, ('?',))[0]} S={idle.get(name, ('?', '?'))[1]}")
            tracks = b.get_tracks()
            if not tracks:
                log("     (no tracks -> this widget is never animated)")
            for t in tracks:
                log(f"     Track {t.get_class().get_name()} '{t.get_display_name()}'")
                try:
                    log(f"       property={t.get_property_path()}")
                except Exception:
                    pass
                for sec in t.get_sections():
                    log(f"       section {sec.get_start_frame()} -> {sec.get_end_frame()}")
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


if __name__ == "__main__":
    main()
