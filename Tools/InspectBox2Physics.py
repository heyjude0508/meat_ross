# Inspect-only wrapper for box_2 physics pop (no simulate/collision/nudge/save).
import os

os.environ["FIX_BOX2_INSPECT_ONLY"] = "1"
script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FixBox2PhysicsPop.py")
with open(script, "r", encoding="utf-8") as f:
    code = compile(f.read(), script, "exec")
exec(code, {"__name__": "__main__", "__file__": script})
