import unreal

def log(m):
    unreal.log(f"[CDFix] {m}"); print(f"[CDFix] {m}")

unreal.EditorAssetLibrary.load_asset("/Game/SubwayTrain/UI_Blueprint/WBP_Chat")
unreal.EditorAssetLibrary.load_asset("/Game/SubwayTrain/UI_Blueprint/WBP_Countdown")
unreal.EditorAssetLibrary.load_asset("/Game/MobilePhone/Blueprint/BP_MobliePhone_L2")

# WBP_Chat tree
chat_widgets = []
for obj in unreal.ObjectIterator(unreal.Widget):
    p = obj.get_path_name()
    if "WBP_Chat.WBP_Chat:WidgetTree." not in p:
        continue
    if "WBP_Chat_C" in p:
        continue
    chat_widgets.append(f"{obj.get_name()}<{obj.get_class().get_name()}>")
log("CHAT_TREE=" + str(sorted(set(chat_widgets))))
cd_in_chat = [x for x in chat_widgets if "Countdown" in x or "WBP_Countdown" in x]
log("COUNTDOWN_IN_CHAT=" + str(cd_in_chat))

# Find any countdown-named widget under chat package
for obj in unreal.ObjectIterator(unreal.Widget):
    p = obj.get_path_name()
    if "WBP_Chat" not in p or "WBP_ChatMsg" in p:
        continue
    if "Countdown" in obj.get_name() or "Countdown" in obj.get_class().get_name():
        log(f"FOUND {obj.get_class().get_name()} name={obj.get_name()} path={p}")
        slot = getattr(obj, "slot", None)
        if isinstance(slot, unreal.CanvasPanelSlot):
            log(f"  anchors={slot.get_anchors()} align={slot.get_alignment()} pos={slot.get_position()} size={slot.get_size()} vis try")
        try:
            log(f"  visibility={obj.get_editor_property('visibility')}")
        except Exception:
            pass

# Countdown tree + tick
cd_tree=[]
for obj in unreal.ObjectIterator(unreal.Widget):
    p=obj.get_path_name()
    if "WBP_Countdown.WBP_Countdown:WidgetTree." in p and "WBP_Countdown_C" not in p:
        cd_tree.append(f"{obj.get_name()}<{obj.get_class().get_name()}>")
log("CD_TREE=" + str(sorted(set(cd_tree))))

# Phone widget class
for obj in unreal.ObjectIterator(unreal.WidgetComponent):
    p=obj.get_path_name()
    if "MobliePhone" in p or "MobilePhone" in p or "BP_Moblie" in p:
        try:
            wc=obj.get_editor_property("widget_class")
        except Exception:
            wc=None
        try:
            ds=obj.get_editor_property("draw_size")
        except Exception:
            ds=None
        log(f"PHONE_WC path={p} class={wc} draw_size={ds}")

log("DONE")
