"""Mirror row A (SizeBox_66) layout config onto row B (SizeBox_127) in WBP_Chat.

Row B is missing the SizeBox that wraps the radial slider, so it gets created and
the overlay children are reordered to match row A (slider first, letter on top).
"""
import os
import shutil
import time

import unreal

PATH = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat"
PREFIX = "/Game/SubwayTrain/UI_Blueprint/WBP_Chat.WBP_Chat:WidgetTree."
UASSET = "E:/game/design/Epic Games/project/meat_ross/Content/SubwayTrain/UI_Blueprint/WBP_Chat.uasset"
BACKUP_DIR = "E:/game/design/Epic Games/project/meat_ross/Saved/Backup"

SLOT_ALIGN_PROPS = ("horizontal_alignment", "vertical_alignment", "padding")


def log(m):
    unreal.log(f"[MirrorB] {m}")


def widgets():
    out = {}
    for obj in unreal.ObjectIterator(unreal.Widget):
        p = obj.get_path_name()
        if p.startswith(PREFIX):
            out[obj.get_name()] = obj
    return out


def backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dst = os.path.join(BACKUP_DIR, f"WBP_Chat_{time.strftime('%Y%m%d_%H%M%S')}.uasset")
    shutil.copy2(UASSET, dst)
    log(f"backup -> {dst}")


def copy_rt(src, dst):
    rt = src.render_transform
    new = unreal.WidgetTransform()
    new.set_editor_property("translation", unreal.Vector2D(rt.translation.x, rt.translation.y))
    new.set_editor_property("scale", unreal.Vector2D(rt.scale.x, rt.scale.y))
    new.set_editor_property("shear", unreal.Vector2D(rt.shear.x, rt.shear.y))
    new.set_editor_property("angle", rt.angle)
    dst.set_editor_property("render_transform", new)
    piv = src.render_transform_pivot
    dst.set_editor_property("render_transform_pivot", unreal.Vector2D(piv.x, piv.y))
    log(f"  RT {src.get_name()} -> {dst.get_name()}: "
        f"T=({rt.translation.x},{rt.translation.y}) S=({rt.scale.x},{rt.scale.y})")


def copy_slot(src, dst, with_size=False):
    ss, ds = src.slot, dst.slot
    if not ss or not ds:
        log(f"  !! slot missing src={ss} dst={ds}")
        return
    for p in SLOT_ALIGN_PROPS:
        try:
            ds.set_editor_property(p, ss.get_editor_property(p))
        except Exception as e:
            log(f"  slot {p} failed on {dst.get_name()}: {e}")
    if with_size:
        try:
            ds.set_editor_property("size", ss.get_editor_property("size"))
        except Exception as e:
            log(f"  slot size failed on {dst.get_name()}: {e}")
    log(f"  Slot {src.get_name()} -> {dst.get_name()} copied")


def copy_sizebox_overrides(src, dst):
    for axis in ("width", "height"):
        val = src.get_editor_property(f"{axis}_override")
        setter = getattr(dst, f"set_{axis}_override")
        clearer = getattr(dst, f"clear_{axis}_override")
        if val and val > 0.0:
            setter(val)
            log(f"  {dst.get_name()} {axis}_override = {val}")
        else:
            clearer()
            log(f"  {dst.get_name()} {axis}_override cleared")


def ensure_slider_sizebox(tree, overlay_b, slider_b, image_b):
    """Wrap slider_b in a SizeBox inside overlay_b; order = [SizeBox, ImageB]."""
    existing = None
    for i in range(overlay_b.get_children_count()):
        c = overlay_b.get_child_at(i)
        if isinstance(c, unreal.SizeBox):
            existing = c
    if existing is not None:
        log(f"  reusing existing SizeBox '{existing.get_name()}' under Overlay_166")
        box = existing
        if not box.has_child(slider_b):
            box.add_child(slider_b)
    else:
        box = unreal.new_object(unreal.SizeBox, outer=tree, name="SizeBox_RadialB")
        log(f"  created SizeBox '{box.get_name()}'")
        overlay_b.remove_child(slider_b)
        box.add_child(slider_b)
        overlay_b.add_child_to_overlay(box)

    # Match row A ordering: slider box first, letter drawn on top.
    if overlay_b.get_child_index(image_b) < overlay_b.get_child_index(box):
        overlay_b.remove_child(image_b)
        overlay_b.add_child_to_overlay(image_b)
        log("  reordered Overlay_166 children -> [SizeBox, ImageB]")
    return box


def copy_image_brush(src_img, dst_img, dst_texture_pkg):
    brush = src_img.get_editor_property("brush")
    tex = unreal.EditorAssetLibrary.load_asset(dst_texture_pkg)
    dst_img.set_editor_property("brush", brush)
    b = dst_img.get_editor_property("brush")
    b.set_editor_property("resource_object", tex)
    dst_img.set_editor_property("brush", b)
    dst_img.set_editor_property("color_and_opacity", src_img.get_editor_property("color_and_opacity"))
    log(f"  brush copied {src_img.get_name()} -> {dst_img.get_name()} (resource kept as {tex.get_name()})")


def main():
    backup()
    bp = unreal.EditorAssetLibrary.load_asset(PATH)
    w = widgets()

    need = ["SizeBox_66", "SizeBox_127", "HorizontalBox_40", "HorizontalBox_229",
            "Overlay_90", "Overlay_166", "SizeBox_129", "RadialSliderA", "RadialSliderB",
            "ImageA", "ImageB", "TextBoxA", "TextBoxB"]
    missing = [n for n in need if n not in w]
    if missing:
        log(f"ABORT missing widgets: {missing}")
        return

    tree = w["Overlay_166"].get_outer()

    log("=== 1. structure: wrap RadialSliderB in a SizeBox ===")
    box_b = ensure_slider_sizebox(tree, w["Overlay_166"], w["RadialSliderB"], w["ImageB"])

    log("=== 2. row container: SizeBox_127 <- SizeBox_66 ===")
    copy_slot(w["SizeBox_66"], w["SizeBox_127"], with_size=True)
    copy_rt(w["SizeBox_66"], w["SizeBox_127"])
    copy_sizebox_overrides(w["SizeBox_66"], w["SizeBox_127"])

    log("=== 3. HorizontalBox_229 <- HorizontalBox_40 ===")
    copy_slot(w["HorizontalBox_40"], w["HorizontalBox_229"])
    copy_rt(w["HorizontalBox_40"], w["HorizontalBox_229"])

    log("=== 4. Overlay_166 <- Overlay_90 ===")
    copy_slot(w["Overlay_90"], w["Overlay_166"], with_size=True)
    copy_rt(w["Overlay_90"], w["Overlay_166"])

    log("=== 5. slider SizeBox <- SizeBox_129 ===")
    copy_slot(w["SizeBox_129"], box_b)
    copy_rt(w["SizeBox_129"], box_b)
    copy_sizebox_overrides(w["SizeBox_129"], box_b)

    log("=== 6. RadialSliderB <- RadialSliderA ===")
    copy_slot(w["RadialSliderA"], w["RadialSliderB"])
    copy_rt(w["RadialSliderA"], w["RadialSliderB"])

    log("=== 7. ImageB <- ImageA ===")
    copy_slot(w["ImageA"], w["ImageB"])
    copy_rt(w["ImageA"], w["ImageB"])
    copy_image_brush(w["ImageA"], w["ImageB"], "/Game/SubwayTrain/UI_Blueprint/B")

    log("=== 8. TextBoxB <- TextBoxA ===")
    copy_slot(w["TextBoxA"], w["TextBoxB"], with_size=True)
    copy_rt(w["TextBoxA"], w["TextBoxB"])

    log("=== 9. compile + save ===")
    if hasattr(unreal, "BlueprintEditorLibrary"):
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            log("  compiled")
        except Exception as e:
            log(f"  compile failed: {e}")
    unreal.EditorAssetLibrary.save_asset(PATH, only_if_is_dirty=False)
    log("  saved")


if __name__ == "__main__":
    main()
