# Dump WBP_Countdown + WBP_Chat CountdownTimer layout (anchors / offsets / alignment).
import unreal

CHAT = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat"
COUNTDOWN = "/Game/SubwayTrain/UI_Blueprint/WBP_Countdown"


def log(m):
    unreal.log(f"[CountdownLayout] {m}")
    print(f"[CountdownLayout] {m}")


def find_widgets(asset_token, name=None, cls=unreal.Widget):
    hits = []
    for obj in unreal.ObjectIterator(cls):
        path = obj.get_path_name()
        if asset_token not in path:
            continue
        if name is not None and obj.get_name() != name:
            continue
        hits.append(obj)
    return hits


def dump_slot(widget, label):
    if not widget:
        log(f"{label}: MISSING")
        return
    path = widget.get_path_name()
    log(f"===== {label} =====")
    log(f"  path={path}")
    log(f"  class={widget.get_class().get_name()}")
    try:
        rt = widget.get_editor_property("render_transform")
        log(f"  RT.translation={rt.translation} scale={rt.scale} angle={rt.angle}")
    except Exception as e:
        log(f"  RT err={e}")
    try:
        vis = widget.get_editor_property("visibility")
        log(f"  visibility={vis}")
    except Exception:
        pass

    slot = getattr(widget, "slot", None)
    if not slot:
        log("  slot=None")
        return
    log(f"  slotClass={slot.get_class().get_name()}")

    if isinstance(slot, unreal.CanvasPanelSlot):
        try:
            layout = slot.get_layout()
            log(f"  layout={layout}")
        except Exception as e:
            log(f"  get_layout err={e}")
        for meth, args in (
            ("get_anchors", ()),
            ("get_offsets", ()),
            ("get_alignment", ()),
            ("get_auto_size", ()),
            ("get_position", ()),
            ("get_size", ()),
            ("get_z_order", ()),
        ):
            try:
                fn = getattr(slot, meth)
                log(f"  {meth}={fn(*args)}")
            except Exception as e:
                log(f"  {meth} err={e}")
        try:
            ad = slot.get_editor_property("layout_data")
            log(f"  layout_data={ad}")
            for p in ("offsets", "anchors", "alignment"):
                try:
                    log(f"  layout_data.{p}={ad.get_editor_property(p)}")
                except Exception:
                    pass
        except Exception as e:
            log(f"  layout_data err={e}")
    else:
        for p in (
            "padding",
            "horizontal_alignment",
            "vertical_alignment",
            "size",
        ):
            try:
                log(f"  {p}={slot.get_editor_property(p)}")
            except Exception:
                pass


def dump_tree_names(asset_token):
    names = []
    for obj in unreal.ObjectIterator(unreal.Widget):
        path = obj.get_path_name()
        if asset_token not in path:
            continue
        if ":WidgetTree." not in path:
            continue
        if f"{asset_token}_C" in path:
            continue
        names.append(f"{obj.get_name()}<{obj.get_class().get_name()}>")
    log(f"WidgetTree({asset_token}): {sorted(set(names))}")


def prefer_designer(hits):
    for h in hits:
        p = h.get_path_name()
        if ":WidgetTree." in p and "_C" not in p.split(":WidgetTree.")[0]:
            return h
    for h in hits:
        if ":WidgetTree." in h.get_path_name():
            return h
    return hits[0] if hits else None


def dump_phone_components():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world:
        log("No editor world")
        return
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        name = actor.get_name()
        cls = actor.get_class().get_name()
        if "Phone" not in name and "Phone" not in cls and "Moblie" not in name and "Moblie" not in cls:
            continue
        log(f"===== Actor {name} ({cls}) =====")
        try:
            t = actor.get_actor_transform()
            log(f"  actorTransform loc={t.translation} rot={t.rotation} scale={t.scale3d}")
        except Exception as e:
            log(f"  transform err={e}")
        for comp in actor.get_components_by_class(unreal.WidgetComponent):
            log(f"  WidgetComponent={comp.get_name()}")
            for p in (
                "widget_class",
                "draw_size",
                "pivot",
                "geometry_mode",
                "blend_mode",
                "draw_at_desired_size",
                "window_focusable",
            ):
                try:
                    log(f"    {p}={comp.get_editor_property(p)}")
                except Exception as e:
                    log(f"    {p} err={e}")
            try:
                space = comp.get_editor_property("space")
                log(f"    space={space}")
            except Exception:
                try:
                    log(f"    widget_space={comp.get_editor_property('widget_space')}")
                except Exception as e:
                    log(f"    space err={e}")
            try:
                rt = comp.get_relative_transform()
                log(f"    relative loc={rt.translation} rot={rt.rotation} scale={rt.scale3d}")
            except Exception as e:
                log(f"    relative err={e}")
            try:
                w = comp.get_widget()
                log(f"    runtimeWidget={w}")
            except Exception as e:
                log(f"    get_widget err={e}")


def main():
    unreal.EditorAssetLibrary.load_asset(CHAT)
    unreal.EditorAssetLibrary.load_asset(COUNTDOWN)

    dump_tree_names("WBP_Countdown")
    dump_tree_names("WBP_Chat")

    # Inside WBP_Countdown itself
    for name in ("CountdownValue", "ProgressBar_73", "CanvasPanel_0", "CanvasPanel"):
        w = prefer_designer(find_widgets("WBP_Countdown", name))
        dump_slot(w, f"Countdown/{name}")

    # Countdown as child of WBP_Chat
    for name in ("CountdownTimer", "Countdown Timer"):
        hits = find_widgets("WBP_Chat", name)
        # also match generated name variants
        if not hits:
            hits = [o for o in unreal.ObjectIterator(unreal.Widget) if "WBP_Chat" in o.get_path_name() and "Countdown" in o.get_name()]
        w = prefer_designer(hits)
        dump_slot(w, f"Chat/{name}")

    # Root canvas children of WBP_Chat that look relevant
    for obj in unreal.ObjectIterator(unreal.Widget):
        path = obj.get_path_name()
        if "WBP_Chat" not in path or ":WidgetTree." not in path:
            continue
        if "WBP_Chat_C" in path:
            continue
        slot = getattr(obj, "slot", None)
        if isinstance(slot, unreal.CanvasPanelSlot):
            dump_slot(obj, f"ChatCanvasChild/{obj.get_name()}")

    dump_phone_components()
    log("DONE")


if __name__ == "__main__":
    main()
