# Second pass: disable volumetric fog with alternate property names.
import unreal

MAP_PATH = "/Game/SubwayTrain/Maps/Subway"


def try_set(obj, names, value):
    for name in names:
        try:
            obj.set_editor_property(name, value)
            unreal.log(f"[OptimizeFog] set {obj.get_name()}.{name}={value}")
            return True
        except Exception:
            continue
    return False


def main():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ExponentialHeightFog)
    unreal.log(f"[OptimizeFog] fog actors={len(actors)}")
    for actor in actors:
        comps = actor.get_components_by_class(unreal.ExponentialHeightFogComponent)
        for comp in comps:
            try_set(comp, ("volumetric_fog", "b_enable_volumetric_fog", "enable_volumetric_fog"), False)
            try_set(comp, ("fog_density",), 0.008)
            try_set(comp, ("fog_max_opacity",), 0.5)
            try_set(comp, ("volumetric_fog_extinction_scale",), 0.0)
            try_set(comp, ("volumetric_fog_distance",), 0.0)

    # Also disable remaining light shadows more aggressively via PointLight/SpotLight actors
    for cls in (unreal.PointLight, unreal.SpotLight, unreal.RectLight):
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, cls):
            for comp in actor.get_components_by_class(unreal.LightComponent):
                try_set(comp, ("cast_shadows",), False)
                try_set(comp, ("cast_dynamic_shadows",), False)
                try_set(comp, ("cast_static_shadows",), False)
                try_set(comp, ("cast_volumetric_shadow",), False)

    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log("[OptimizeFog] Done")


if __name__ == "__main__":
    main()
