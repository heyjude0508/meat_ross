import unreal
PREFIX="/Game/SubwayTrain/UI_Blueprint/WBP_Chat.WBP_Chat:WidgetTree."

def find(name):
    for obj in unreal.ObjectIterator(unreal.Widget):
        p=obj.get_path_name()
        if p.startswith(PREFIX) and "WBP_Chat_C" not in p and obj.get_name()==name:
            return obj
    return None

def log(m):
    unreal.log(f"[AB] {m}"); print(f"[AB] {m}")

a=find("TextBoxA"); b=find("TextBoxB")
log(f"A class={a.get_class().get_name()} B class={b.get_class().get_name()}")
# B style font
style=b.get_editor_property("widget_style")
for attr in ("font","foreground_color","background_color","padding","read_only_foreground_color"):
    try:
        v=style.get_editor_property(attr)
        log(f"B.style.{attr}={v}")
    except Exception as e:
        log(f"B.style.{attr} err {e}")
try:
    font=style.get_editor_property("font")
    log(f"B font size={font.get_editor_property('size')} typeface={font.get_editor_property('typeface_font_name')}")
except Exception as e:
    log(f"B font detail {e}")

# A color
try: log(f"A color={a.get_editor_property('color_and_opacity')}")
except Exception as e: log(str(e))
try: log(f"A just={a.get_editor_property('justification')}")
except Exception as e: log(str(e))
try: log(f"A wrap={a.get_editor_property('auto_wrap_text')}")
except Exception as e: log(str(e))

# SizeBox overrides
for n in ("SizeBox_66","SizeBox_127"):
    s=find(n)
    log(f"{n} w={s.get_editor_property('width_override')} h={s.get_editor_property('height_override')} minW={s.get_editor_property('min_desired_width')} minH={s.get_editor_property('min_desired_height')}")
    try:
        log(f"  ovW={s.get_editor_property('b_override_width_override')} ovH={s.get_editor_property('b_override_height_override')}")
    except Exception: pass
