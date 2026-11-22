import unreal

_intro_seen = set()
def _intro_verify(delta):
    worlds = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not worlds:
        return
    t = unreal.GameplayStatics.get_time_seconds(worlds)
    bucket = next((x for x in [0,2,4,6,9] if t >= x and x not in _intro_seen), None)
    if bucket is None:
        return
    _intro_seen.add(bucket)
    pc = unreal.GameplayStatics.get_player_controller(worlds, 0)
    pawn = pc.get_controlled_pawn() if pc else None
    manager = pc.player_camera_manager if pc else None
    print('INTRO_VERIFY', round(t,2), 'pawn', pawn, 'hidden', pawn.get_editor_property('hidden') if pawn else None,
          'yaw', manager.get_camera_rotation().yaw if manager else None,
          'look_blocked', pc.is_look_input_ignored() if pc else None,
          'move_blocked', pc.is_move_input_ignored() if pc else None)
    if bucket == 9:
        unreal.unregister_slate_pre_tick_callback(_intro_verify_handle)
_intro_verify_handle = unreal.register_slate_pre_tick_callback(_intro_verify)
print('INTRO_VERIFY_ARMED')
