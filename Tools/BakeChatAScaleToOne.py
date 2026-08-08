# Bake ImageA + Overlay_90 render Scale into layout size, then reset Scale to 1.
import unreal
import math

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat"


def log(m):
    unreal.log(f"[BakeScale] {m}")


def find_widget(name):
    hits = []
    for obj in unreal.ObjectIterator(unreal.Widget):
        path = obj.get_path_name()
        if f"WBP_Chat:WidgetTree.{name}" not in path:
            continue
        if "WBP_Chat_C" in path:
            continue
        hits.append(obj)
    return hits[0] if hits else None


def get_rt(w):
    return w.get_editor_property("render_transform")


def set_rt(w, translation=None, scale=None, shear=None, angle=None):
    rt = get_rt(w)
    if translation is not None:
        t = unreal.Vector2D(float(translation[0]), float(translation[1]))
        rt.set_editor_property("translation", t)
    if scale is not None:
        s = unreal.Vector2D(float(scale[0]), float(scale[1]))
        rt.set_editor_property("scale", s)
    if shear is not None:
        sh = unreal.Vector2D(float(shear[0]), float(shear[1]))
        rt.set_editor_property("shear", sh)
    if angle is not None:
        rt.set_editor_property("angle", float(angle))
    w.set_editor_property("render_transform", rt)
    # Also set pivot center for predictable scale
    w.set_editor_property("render_transform_pivot", unreal.Vector2D(0.5, 0.5))


def try_measure_widget_class():
    """Create a transient widget instance and read desired sizes if possible."""
    wbp = unreal.EditorAssetLibrary.load_asset(PATH)
    cls = wbp.generated_class()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    # create without player
    try:
        widget = unreal.WidgetBlueprintLibrary.create(world, cls, None)
    except Exception as e:
        log(f"create widget failed: {e}")
        return None
    if not widget:
        return None
    try:
        # Force rebuild
        if hasattr(widget, "force_layout_prepass"):
            widget.force_layout_prepass()
    except Exception:
        pass
    sizes = {}
    for name in ("Overlay_90", "ImageA", "RadialSliderA", "SizeBox_66", "TextBoxA"):
        try:
            # Find named widget from UserWidget
            w = widget.get_widget_from_name(name)
            if not w:
                continue
            try:
                ds = w.get_desired_size()
                sizes[name] = (ds.x, ds.y)
                log(f"measured {name} desired={ds}")
            except Exception as e:
                log(f"desired {name}: {e}")
            try:
                geo = w.get_cached_geometry()
                local = geo.get_local_size()
                sizes[name + "_local"] = (local.x, local.y)
                log(f"measured {name} local={local}")
            except Exception as e:
                log(f"geo {name}: {e}")
        except Exception as e:
            log(f"get {name}: {e}")
    try:
        widget.remove_from_parent()
    except Exception:
        pass
    return sizes


def main():
    unreal.EditorAssetLibrary.load_asset(PATH)

    overlay = find_widget("Overlay_90")
    image = find_widget("ImageA")
    slider = find_widget("RadialSliderA")
    if not overlay or not image:
        log(f"ERROR overlay={overlay} image={image}")
        return

    ort = get_rt(overlay)
    irt = get_rt(image)
    log(f"BEFORE Overlay_90 T={ort.translation} S={ort.scale}")
    log(f"BEFORE ImageA T={irt.translation} S={irt.scale}")
    if slider:
        srt = get_rt(slider)
        log(f"BEFORE RadialSliderA T={srt.translation} S={srt.scale}")

    ox, oy = float(ort.scale.x), float(ort.scale.y)
    ix, iy = float(irt.scale.x), float(irt.scale.y)

    sizes = try_measure_widget_class() or {}

    # Determine layout size of Overlay (pre-render-transform)
    layout_w = None
    layout_h = None
    if "Overlay_90_local" in sizes and sizes["Overlay_90_local"][0] > 1:
        layout_w, layout_h = sizes["Overlay_90_local"]
    elif "Overlay_90" in sizes and sizes["Overlay_90"][0] > 1:
        layout_w, layout_h = sizes["Overlay_90"]

    # Fallback estimate from translation compensation:
    # with pivot 0.5, left-gap from scaleX = layoutW*(1-sx)/2 ≈ -translation if used to left-align
    if layout_w is None:
        # From earlier: translation -90, scale 0.45 => layoutW ≈ 90 / ((1-0.45)/2) = 327.27
        tx = abs(float(ort.translation.x))
        if ox < 0.999 and tx > 0:
            layout_w = tx / ((1.0 - ox) / 2.0)
        else:
            layout_w = 160.0
        layout_h = layout_w  # square-ish avatar column fallback
        if "SizeBox_66_local" in sizes and sizes["SizeBox_66_local"][1] > 1:
            layout_h = sizes["SizeBox_66_local"][1]
        log(f"estimated layout from translation: {layout_w} x {layout_h}")

    visual_w = layout_w * ox
    visual_h = layout_h * oy
    log(f"target visual size ≈ {visual_w} x {visual_h} (from layout {layout_w}x{layout_h} * scale {ox}x{oy})")

    # --- Bake Overlay_90 ---
    # 1) Prefer SizeBox parent override if hierarchy has SizeBox_66 wrapping the row.
    #    Put fixed size on Overlay via changing HB slot to Auto and wrapping... 
    #    Simplest: set Overlay HB slot to Auto and set Overlay's slot padding 0,
    #    then use a SizeBox already in tree OR set min desired sizes via wrap.
    #
    # Overlay is ContentWidget children holder. We'll set its HorizontalBoxSlot to Automatic
    # and apply SizeBox_66 height + give Overlay a sibling-free fixed size using
    # unreal.SizeBox around it if needed.
    #
    # Practical approach used here:
    # - Find parent HorizontalBox and Overlay's slot
    # - Set Overlay slot size rule Auto
    # - Create/find SizeBox wrapping is hard without graph; instead set render scale 1
    #   and set SizeBox_66 width/height overrides to bake row, while Overlay fill
    #   gets constrained by changing Overlay scale bake into SizeBox that only wraps overlay.
    #
    # Since we can't easily reparent in Python reliably, bake by:
    # A) Setting SizeBox_66 WidthOverride/HeightOverride if Overlay is the avatar column
    #    Actually SizeBox wraps whole row (overlay+textbox). So don't shrink whole row.
    #
    # B) Change Overlay_90 HorizontalBoxSlot from Fill to Auto, and set
    #    Overlay's... Overlay has no width override.
    #    Use Image brush size + RadialSlider won't set Overlay size well.
    #
    # Best available without reparent: use slot padding tricks? No.
    #
    # Reparent Overlay into a new SizeBox via WidgetTree API if available.

    tree = None
    for obj in unreal.ObjectIterator(unreal.WidgetTree):
        if obj.get_path_name().endswith("WBP_Chat:WidgetTree"):
            tree = obj
            break
    log(f"WidgetTree={tree}")

    # Try WidgetTree.replace_widget / remove / construct
    sizebox_for_overlay = None
    if tree:
        # See if there's already a dedicated size box - create one in tree
        try:
            sizebox_for_overlay = tree.construct_widget(unreal.SizeBox.static_class(), "SizeBox_OverlayA")
            log(f"constructed {sizebox_for_overlay}")
        except Exception as e:
            log(f"construct SizeBox failed: {e}")

    baked_via_sizebox = False
    if tree and sizebox_for_overlay and overlay.slot and isinstance(overlay.slot, unreal.HorizontalBoxSlot):
        hb = None
        # find parent HB by scanning
        for obj in unreal.ObjectIterator(unreal.HorizontalBox):
            path = obj.get_path_name()
            if "WBP_Chat:WidgetTree" not in path or "WBP_Chat_C" in path:
                continue
            try:
                for i in range(obj.get_children_count()):
                    if obj.get_child_at(i) == overlay:
                        hb = obj
                        break
            except Exception:
                continue
            if hb:
                break
        log(f"parent HB={hb}")
        if hb:
            try:
                # Remember index
                index = None
                for i in range(hb.get_children_count()):
                    if hb.get_child_at(i) == overlay:
                        index = i
                        break
                # Remove overlay from HB, put into SizeBox, insert SizeBox at index
                # WidgetTree APIs:
                # tree.remove_widget(overlay) might detach
                try:
                    hb.remove_child(overlay)
                except Exception:
                    try:
                        unreal.WidgetHierarchyLibrary  # may not exist
                    except Exception:
                        pass
                    # fallback PanelWidget
                    hb.remove_child_at(index)

                sizebox_for_overlay.set_content(overlay)
                sizebox_for_overlay.set_editor_property("width_override", float(visual_w))
                sizebox_for_overlay.set_editor_property("height_override", float(visual_h))
                # enable overrides - property names differ by version
                for flag, val in (
                    ("width_override_enabled", True),
                    ("height_override_enabled", True),
                    ("b_override_width", True),
                    ("b_override_height", True),
                ):
                    try:
                        sizebox_for_overlay.set_editor_property(flag, val)
                    except Exception:
                        pass
                # Also try setattr style used in some UE versions
                for flag in ("override_width", "override_height"):
                    # boolean often paired: set by setting override value > 0 and using set_width_override method
                    pass
                try:
                    sizebox_for_overlay.set_width_override(float(visual_w))
                    sizebox_for_overlay.set_height_override(float(visual_h))
                except Exception as e:
                    log(f"set_width/height_override methods: {e}")

                # Insert sizebox into HB at same index
                if index is None:
                    index = 0
                try:
                    hb.insert_child_at(index, sizebox_for_overlay)
                except Exception:
                    hb.add_child(sizebox_for_overlay)
                    # try move - if add appends, may be wrong order; attempt insert via slot
                slot = sizebox_for_overlay.slot
                if isinstance(slot, unreal.HorizontalBoxSlot):
                    slot.set_editor_property("size", unreal.SlateChildSize(1.0, unreal.SlateSizeRule.AUTOMATIC))
                    slot.set_editor_property("horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_LEFT)
                    slot.set_editor_property("vertical_alignment", unreal.VerticalAlignment.V_ALIGN_CENTER)
                    # zero padding
                    m = unreal.Margin(0, 0, 0, 0)
                    slot.set_editor_property("padding", m)
                log("Reparented Overlay_90 under SizeBox_OverlayA with baked size")
                baked_via_sizebox = True
            except Exception as e:
                log(f"reparent failed: {e}")
                import traceback
                log(traceback.format_exc())

    # Reset Overlay transform to identity scale; clear translation if baked into sizebox
    if baked_via_sizebox:
        set_rt(overlay, translation=(0.0, 0.0), scale=(1.0, 1.0), shear=(0.0, 0.0), angle=0.0)
    else:
        # Fallback: keep approximate left alignment by zeroing scale and using padding on slot
        set_rt(overlay, translation=(0.0, 0.0), scale=(1.0, 1.0), shear=(0.0, 0.0), angle=0.0)
        if isinstance(overlay.slot, unreal.HorizontalBoxSlot):
            # Switch to Auto and hope content desired size works; set fill false
            try:
                overlay.slot.set_editor_property("size", unreal.SlateChildSize(float(visual_w), unreal.SlateSizeRule.AUTOMATIC))
            except Exception:
                overlay.slot.set_editor_property("size", unreal.SlateChildSize(1.0, unreal.SlateSizeRule.AUTOMATIC))
            overlay.slot.set_editor_property("horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_LEFT)
            overlay.slot.set_editor_property("vertical_alignment", unreal.VerticalAlignment.V_ALIGN_CENTER)
            log("Fallback: Overlay scale=1, slot Auto (visual size may need manual SizeBox tweak)")

    # --- Bake ImageA ---
    # Image fills Overlay; with Overlay now at visual size, Image scale 1 fills correctly.
    # Combined previous visual scale of image relative to overlay was ix/iy.
    # If we want Image visual same within old overlay visual: after overlay bake,
    # Image should be scale 1 and fill. Old Image scale was additional shrink inside overlay.
    # Old visual image size ≈ layout_overlay * overlay_scale * image_scale
    # New overlay size = visual_w/h = layout * overlay_scale
    # So Image at scale 1 filling new overlay = layout*overlay_scale = old overlay visual
    # But old Image visual was smaller by image_scale (0.8 x 0.9).
    # To preserve ImageA visual size exactly, either:
    #   - keep image slightly smaller via padding, or
    #   - set SizeBox smaller by image scale, or  
    #   - set brush/margin
    # User said both current sizes are desired. So final Image visual = old Image visual
    # = visual_overlay * image_scale.
    img_visual_w = visual_w * ix
    img_visual_h = visual_h * iy
    log(f"ImageA target visual ≈ {img_visual_w} x {img_visual_h}")

    # If Overlay sizebox is the outer bake, shrink it to image visual OR pad Image.
    # Cleaner: Overlay sizebox uses image visual size (avatar is the content), Image+Slider fill it at scale 1.
    # User wants Overlay's current *visual* size (already includes overlay scale) AND Image's current visual.
    # Image visual is smaller than Overlay visual. So Overlay box stays visual_w/h, Image at scale 1 Fill will be LARGER than before.
    # To keep Image same size inside: use padding on Image overlay slot, or keep a uniform scale... user wants scale 1.
    # Use OverlaySlot padding to inset Image (and optionally slider) so drawn content matches old scaled size.
    pad_x = max(0.0, (visual_w - img_visual_w) / 2.0)
    pad_y = max(0.0, (visual_h - img_visual_h) / 2.0)
    # Actually old image was scaled with pivot center + translation -4. Approx inset:
    # With Fill + scale 0.8 from center, margin fraction (1-0.8)/2 = 0.1 of overlay visual each side.
    pad_x = visual_w * (1.0 - ix) / 2.0
    pad_y = visual_h * (1.0 - iy) / 2.0
    log(f"ImageA inset padding ≈ {pad_x}, {pad_y}")

    set_rt(image, translation=(0.0, 0.0), scale=(1.0, 1.0), shear=(0.0, 0.0), angle=0.0)
    if isinstance(image.slot, unreal.OverlaySlot):
        m = unreal.Margin(pad_x, pad_y, pad_x, pad_y)
        image.slot.set_editor_property("padding", m)
        image.slot.set_editor_property("horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_FILL)
        image.slot.set_editor_property("vertical_alignment", unreal.VerticalAlignment.V_ALIGN_FILL)

    # RadialSlider should match Image fill of overlay (old slider scale 0.9)
    if slider:
        set_rt(slider, translation=(0.0, 0.0), scale=(1.0, 1.0), shear=(0.0, 0.0), angle=0.0)
        if isinstance(slider.slot, unreal.OverlaySlot):
            # old scale 0.9 => slight inset
            sx = float(get_rt(slider).scale.x)  # already 1
            # use previous known 0.9
            spx = visual_w * (1.0 - 0.9) / 2.0
            spy = visual_h * (1.0 - 0.9) / 2.0
            # Actually we already reset scale; read from before: was 0.9
            spx = visual_w * 0.05
            spy = visual_h * 0.05
            slider.slot.set_editor_property("padding", unreal.Margin(spx, spy, spx, spy))
            slider.slot.set_editor_property("horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_FILL)
            slider.slot.set_editor_property("vertical_alignment", unreal.VerticalAlignment.V_ALIGN_FILL)

    # If sizebox exists, set override size to Overlay visual
    if sizebox_for_overlay and baked_via_sizebox:
        try:
            sizebox_for_overlay.set_width_override(float(visual_w))
            sizebox_for_overlay.set_height_override(float(visual_h))
        except Exception:
            try:
                sizebox_for_overlay.set_editor_property("width_override", float(visual_w))
                sizebox_for_overlay.set_editor_property("height_override", float(visual_h))
            except Exception as e:
                log(f"sizebox size set err {e}")

    # Verify
    ort2 = get_rt(overlay)
    irt2 = get_rt(image)
    log(f"AFTER Overlay_90 T={ort2.translation} S={ort2.scale}")
    log(f"AFTER ImageA T={irt2.translation} S={irt2.scale}")

    wbp = unreal.EditorAssetLibrary.load_asset(PATH)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(wbp)
        log("Compiled")
    except Exception as e:
        log(f"compile: {e}")
    unreal.EditorAssetLibrary.save_asset(PATH)
    log("Saved")


if __name__ == "__main__":
    main()
