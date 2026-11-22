import unreal
sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level('/Game/SubwayTrain/Maps/Subway')
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
for a in actors:
    if any(s in a.get_class().get_name().lower() for s in ['pawn', 'camera', 'playerstart', 'gamemode', 'sequence']):
        print('INTRO_ACTOR', a.get_path_name(), a.get_class().get_name(), a.get_actor_location(), a.get_actor_rotation())
        for c in a.get_components_by_class(unreal.CameraComponent):
            print('INTRO_CAMERA', c.get_name(), c.get_world_location(), c.get_world_rotation(), c.field_of_view)
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print('INTRO_WORLD', w.get_world_settings().get_editor_property('default_game_mode'))
seq = unreal.load_asset('/Game/SubwayTrain/Cinematics/LS_SubwayIntro')
print('INTRO_EXISTING', seq)
if seq:
    print('INTRO_TRACKS', seq.get_tracks())
    for b in seq.get_bindings():
        print('INTRO_BINDING', b.get_name(), b.get_id(), b.get_tracks())
