# Dump emissive-related params on ceiling light materials.
import unreal

MATS = [
    "/Game/Office/Materials/Mi_CeilingLight_01a",
    "/Game/Office/Materials/Mi_CeilingLight_01b",
    "/Game/Office/Materials/Mi_Ceiling",
]


def log(m):
    unreal.log(f"[CeilMat] {m}")


def dump_mi(path):
    mi = unreal.EditorAssetLibrary.load_asset(path)
    log(f"=== {path} class={mi.get_class().get_name() if mi else None} ===")
    if not mi:
        return
    try:
        parent = mi.get_editor_property("parent")
        log(f"  parent={parent}")
    except Exception as e:
        log(f"  parent err {e}")
    # scalar / vector / texture params via MaterialEditingLibrary
    try:
        scalars = unreal.MaterialEditingLibrary.get_scalar_parameter_names(mi)
        for n in scalars:
            v = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, n)
            log(f"  scalar {n}={v}")
    except Exception as e:
        log(f"  scalar err {e}")
    try:
        vectors = unreal.MaterialEditingLibrary.get_vector_parameter_names(mi)
        for n in vectors:
            v = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mi, n)
            log(f"  vector {n}={v}")
    except Exception as e:
        log(f"  vector err {e}")
    try:
        textures = unreal.MaterialEditingLibrary.get_texture_parameter_names(mi)
        for n in textures:
            v = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mi, n)
            log(f"  texture {n}={v}")
    except Exception as e:
        log(f"  texture err {e}")


def main():
    for p in MATS:
        dump_mi(p)
    log("Done")


if __name__ == "__main__":
    main()
