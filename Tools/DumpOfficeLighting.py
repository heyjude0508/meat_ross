# Dump Office map lighting state for diagnosis.
import unreal

MAP_PATH = "/Game/Office/Maps/Office"


def log(msg):
    unreal.log(f"[DumpOfficeLighting] {msg}")


def safe_get(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def dump_light_component(comp, prefix="  "):
    if comp is None:
        return
    cls = comp.get_class().get_name()
    intensity = safe_get(comp, "intensity")
    if intensity is None:
        intensity = safe_get(comp, "Intensity")
    color = safe_get(comp, "light_color")
    if color is None:
        color = safe_get(comp, "LightColor")
    visible = safe_get(comp, "visible")
    if visible is None:
        visible = safe_get(comp, "bVisible")
    enabled = safe_get(comp, "visible_flag")
    affect = safe_get(comp, "affects_world")
    if affect is None:
        affect = safe_get(comp, "bAffectsWorld")
    cast_shadows = safe_get(comp, "cast_shadows")
    if cast_shadows is None:
        cast_shadows = safe_get(comp, "CastShadows")
    mobility = safe_get(comp, "mobility")
    temp = safe_get(comp, "temperature")
    use_temp = safe_get(comp, "use_temperature")
    ies = safe_get(comp, "ies_texture")
    atten = safe_get(comp, "attenuation_radius")
    source_radius = safe_get(comp, "source_radius")
    indirect = safe_get(comp, "indirect_lighting_intensity")
    volumetric = safe_get(comp, "volumetric_scattering_intensity")
    log(
        f"{prefix}{cls} intensity={intensity} color={color} visible={visible} "
        f"affects_world={affect} shadows={cast_shadows} mobility={mobility} "
        f"temp={temp}/{use_temp} atten={atten} source_r={source_radius} "
        f"indirect={indirect} volumetric={volumetric} ies={ies}"
    )


def dump_skylight(actor):
    comps = actor.get_components_by_class(unreal.SkyLightComponent)
    for c in comps:
        intensity = safe_get(c, "intensity")
        real_time = safe_get(c, "real_time_capture")
        source_type = safe_get(c, "source_type")
        cubemap = safe_get(c, "cubemap")
        lower_hem = safe_get(c, "lower_hemisphere_is_black")
        ao = safe_get(c, "occlusion_max_distance")
        log(
            f"  SkyLight intensity={intensity} realtime={real_time} "
            f"source={source_type} cubemap={cubemap} lower_black={lower_hem} "
            f"occ_max={ao} visible={safe_get(c,'visible')} affects={safe_get(c,'affects_world')}"
        )


def dump_ppv(actor):
    comps = actor.get_components_by_class(unreal.PostProcessComponent)
    # PostProcessVolume uses settings property
    enabled = safe_get(actor, "b_enabled")
    if enabled is None:
        enabled = safe_get(actor, "bEnabled")
    unbound = safe_get(actor, "b_unbound")
    if unbound is None:
        unbound = safe_get(actor, "bUnbound")
    priority = safe_get(actor, "priority")
    settings = safe_get(actor, "settings")
    log(f"  PPV enabled={enabled} unbound={unbound} priority={priority}")
    if settings is None:
        return
    # Try common exposure / GI related fields
    fields = [
        "auto_exposure_method",
        "auto_exposure_bias",
        "auto_exposure_min_brightness",
        "auto_exposure_max_brightness",
        "auto_exposure_speed_up",
        "auto_exposure_speed_down",
        "bloom_intensity",
        "ambient_cubemap_intensity",
        "indirect_lighting_intensity",
        "ambient_occlusion_intensity",
        "color_saturation",
        "color_contrast",
        "color_gamma",
        "color_gain",
        "color_offset",
        "vignette_intensity",
        "scene_color_tint",
        "override_auto_exposure_bias",
        "override_auto_exposure_method",
        "override_auto_exposure_min_brightness",
        "override_auto_exposure_max_brightness",
        "override_indirect_lighting_intensity",
        "override_ambient_cubemap_intensity",
    ]
    for f in fields:
        v = safe_get(settings, f)
        if v is not None:
            log(f"    settings.{f}={v}")


def main():
    log(f"Loading {MAP_PATH}")
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    log(f"World={world.get_path_name()}")

    # World settings / lightmass
    ws = unreal.GameplayStatics.get_actor_of_class(world, unreal.WorldSettings)
    if ws:
        force_no = safe_get(ws, "force_no_precomputed_lighting")
        if force_no is None:
            force_no = safe_get(ws, "bForceNoPrecomputedLighting")
        lightmass = safe_get(ws, "lightmass_settings")
        log(f"WorldSettings force_no_precomputed={force_no} lightmass={lightmass}")

    # CVars that matter
    for cvar in (
        "r.DynamicGlobalIlluminationMethod",
        "r.ReflectionMethod",
        "r.Shadow.Virtual.Enable",
        "r.GenerateMeshDistanceFields",
        "r.SkylightIntensityMultiplier",
        "r.DefaultFeature.AutoExposure",
        "r.EyeAdaptationQuality",
        "sg.GlobalIlluminationQuality",
        "sg.ShadowQuality",
        "sg.PostProcessQuality",
    ):
        try:
            val = unreal.SystemLibrary.get_console_variable_int_value(cvar)
            log(f"CVar {cvar}={val}")
        except Exception:
            try:
                # float fallback via execute and hope log shows; skip
                log(f"CVar {cvar}=<unreadable via int>")
            except Exception:
                pass

    light_classes = [
        unreal.DirectionalLight,
        unreal.SkyLight,
        unreal.PointLight,
        unreal.SpotLight,
        unreal.RectLight,
        unreal.PostProcessVolume,
        unreal.ExponentialHeightFog,
        unreal.SkyAtmosphere,
        unreal.VolumetricCloud,
        unreal.ReflectionCapture,
        unreal.SphereReflectionCapture,
        unreal.BoxReflectionCapture,
    ]

    for cls in light_classes:
        actors = list(unreal.GameplayStatics.get_all_actors_of_class(world, cls))
        log(f"=== {cls.__name__}: {len(actors)} ===")
        for a in actors:
            label = a.get_actor_label()
            try:
                hidden = a.is_actor_hidden_in_game()
            except Exception:
                try:
                    hidden = a.get_editor_property("b_hidden")
                except Exception:
                    hidden = "?"
            log(f"- {label} hidden={hidden} class={a.get_class().get_name()}")
            if isinstance(a, unreal.SkyLight):
                dump_skylight(a)
            elif isinstance(a, unreal.PostProcessVolume):
                dump_ppv(a)
            elif isinstance(a, unreal.ExponentialHeightFog):
                comps = a.get_components_by_class(unreal.ExponentialHeightFogComponent)
                for c in comps:
                    log(
                        f"  fog density={safe_get(c,'fog_density')} "
                        f"height_falloff={safe_get(c,'fog_height_falloff')} "
                        f"inscattering={safe_get(c,'fog_inscattering_color')} "
                        f"vol_fog={safe_get(c,'b_enable_volumetric_fog')} "
                        f"vol_ext={safe_get(c,'volumetric_fog_extinction_scale')}"
                    )
            else:
                # generic light actors
                for light_cls in (
                    unreal.LightComponent,
                    unreal.DirectionalLightComponent,
                    unreal.PointLightComponent,
                    unreal.SpotLightComponent,
                    unreal.RectLightComponent,
                ):
                    comps = a.get_components_by_class(light_cls)
                    for c in comps:
                        dump_light_component(c)

    # Also scan Blueprint actors that contain lights
    all_actors = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor))
    bp_lights = 0
    for a in all_actors:
        comps = a.get_components_by_class(unreal.LightComponent)
        if not comps:
            continue
        # skip pure light actors already dumped
        if a.get_class().get_name() in (
            "DirectionalLight",
            "SkyLight",
            "PointLight",
            "SpotLight",
            "RectLight",
            "SpotLightActor",
            "PointLightActor",
        ):
            continue
        bp_lights += 1
        log(f"BP/Actor with lights: {a.get_actor_label()} ({a.get_class().get_name()}) x{len(list(comps))}")
        for c in comps:
            dump_light_component(c)
    log(f"Extra actors with LightComponent: {bp_lights}")
    log("Done")


if __name__ == "__main__":
    main()
