import unreal

MAP = '/Game/SubwayTrain/Maps/Subway'
PATH = '/Game/SubwayTrain/Cinematics/LS_SubwayIntro'
es = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world.get_name() != 'Subway':
    raise RuntimeError('Open Subway before running this script')

# Read the actual pawn camera template, including VR origin offsets.
bp = unreal.load_object(None, '/Game/VRTemplate/Blueprints/VRPawn.VRPawn')
cdo = unreal.get_default_object(bp.generated_class())
for name in ['camera', 'Camera', 'VRCamera', 'VROrigin']:
    try:
        obj = cdo.get_editor_property(name)
        print('INTRO_TEMPLATE', name, obj, obj.get_editor_property('relative_location'))
    except Exception:
        pass
print('INTRO_CDO_COMPONENTS', cdo.get_components_by_class(unreal.CameraComponent))
print('INTRO_READY')
start = next(a for a in es.get_all_level_actors() if isinstance(a, unreal.PlayerStart))
pawn = es.spawn_actor_from_class(bp.generated_class(), start.get_actor_location(), start.get_actor_rotation(), transient=True)
cam = pawn.get_components_by_class(unreal.CameraComponent)[0]
location = cam.get_world_location()
rotation = cam.get_world_rotation()
fov = cam.field_of_view
print('INTRO_POSE', location, rotation, fov)
es.destroy_actor(pawn)

# VR tracking supplies standing head height at runtime; use that eye height for the cinematic.
location.z += 170.0
fov = 90.0
seq = unreal.load_asset(PATH) if unreal.EditorAssetLibrary.does_asset_exist(PATH) else unreal.AssetToolsHelpers.get_asset_tools().create_asset('LS_SubwayIntro', '/Game/SubwayTrain/Cinematics', unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
seq.set_display_rate(unreal.FrameRate(30, 1))
seq.set_playback_start(0)
seq.set_playback_end(240)
camera = next((a for a in es.get_all_level_actors() if a.get_actor_label() == 'Subway_IntroCamera'), None)
if camera is None:
    camera = es.spawn_actor_from_class(unreal.CameraActor, location, rotation)
camera.set_actor_location(location, False, False)
camera.set_actor_label('Subway_IntroCamera')
camera.set_folder_path('Cinematics')
camera.get_component_by_class(unreal.CameraComponent).set_field_of_view(fov)
binding = next((b for b in seq.get_bindings() if b.get_name() == camera.get_actor_label()), None)
if binding is None:
    binding = seq.add_possessable(camera)
track = next((t for t in binding.get_tracks() if isinstance(t, unreal.MovieScene3DTransformTrack)), None)
if track is None:
    track = binding.add_track(unreal.MovieScene3DTransformTrack)
section = track.get_sections()[0] if track.get_sections() else track.add_section()
section.set_range(0, 240)
section.set_completion_mode(unreal.MovieSceneCompletionMode.RESTORE_STATE)
channels = section.get_all_channels()
values = [location.x, location.y, location.z, rotation.roll, rotation.pitch, rotation.yaw, 1., 1., 1.]
for ch, value in zip(channels, values):
    ch.set_default(value)
yaw = channels[5]
for frame, offset in [(0,0), (15,0), (105,80), (135,80), (225,0), (240,0)]:
    if not any(k.get_time().frame_number.value == frame for k in yaw.get_keys()):
        yaw.add_key(unreal.FrameNumber(frame), rotation.yaw + offset, interpolation=unreal.MovieSceneKeyInterpolation.AUTO)
cuts = next((t for t in seq.get_tracks() if isinstance(t, unreal.MovieSceneCameraCutTrack)), None)
if cuts is None:
    cuts = seq.add_track(unreal.MovieSceneCameraCutTrack)
cut = cuts.get_sections()[0] if cuts.get_sections() else cuts.add_section()
cut.set_range(0,240)
camera_id = unreal.MovieSceneObjectBindingID()
camera_id.set_editor_property('guid', binding.get_id())
cut.set_camera_binding_id(camera_id)
# Keep the large in-world phone from blocking the carriage establishing shot.
phone = next((a for a in es.get_all_level_actors() if a.get_actor_label() == 'SM_MobilePhone'), None)
if phone:
    phone_binding = next((b for b in seq.get_bindings() if b.get_name() == phone.get_actor_label()), None)
    if phone_binding is None:
        phone_binding = seq.add_possessable(phone)
    visibility = next((t for t in phone_binding.get_tracks() if isinstance(t, unreal.MovieSceneVisibilityTrack)), None)
    if visibility is None:
        visibility = phone_binding.add_track(unreal.MovieSceneVisibilityTrack)
        visibility.set_property_name_and_path('bHidden', 'bHidden')
    visibility_section = visibility.get_sections()[0] if visibility.get_sections() else visibility.add_section()
    visibility_section.set_range(0,240)
    visibility_section.set_completion_mode(unreal.MovieSceneCompletionMode.RESTORE_STATE)
    visibility_section.get_all_channels()[0].set_default(False)
actor = next((a for a in es.get_all_level_actors() if a.get_actor_label() == 'Subway_Intro_Autoplay'), None)
if actor is None:
    actor = es.spawn_actor_from_class(unreal.LevelSequenceActor, unreal.Vector(0,0,0))
actor.set_actor_label('Subway_Intro_Autoplay')
actor.set_folder_path('Cinematics')
actor.set_sequence(seq)
settings = unreal.MovieSceneSequencePlaybackSettings()
for key, value in dict(auto_play=True, hide_player=True, hide_hud=True, disable_movement_input=True, disable_look_at_input=True, pause_at_end=False).items():
    settings.set_editor_property(key, value)
settings.set_editor_property('finish_completion_state_override', unreal.MovieSceneCompletionModeOverride.FORCE_RESTORE_STATE)
actor.set_editor_property('playback_settings', settings)
unreal.EditorAssetLibrary.save_loaded_asset(seq)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
print('INTRO_BUILT', seq.get_path_name(), location, rotation)
