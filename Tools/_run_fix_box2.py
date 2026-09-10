import sys
import time

sys.path.insert(
    0,
    r"E:\game\design\Epic Games\UE_5.7\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python",
)
from remote_execution import RemoteExecution, MODE_EXEC_FILE

remote = RemoteExecution()
remote.start()
try:
    nodes = []
    for i in range(12):
        time.sleep(0.5)
        nodes = remote.remote_nodes
        print(f"try {i}: nodes={nodes}")
        if nodes:
            break
    if not nodes:
        print("NO_NODES")
        raise SystemExit(2)
    node_id = nodes[0]["node_id"]
    print("connecting", node_id)
    remote.open_command_connection(node_id)
    cmd = r"E:/game/design/Epic Games/project/meat_ross/Tools/FixBox2PhysicsPop.py"
    result = remote.run_command(cmd, unattended=True, exec_mode=MODE_EXEC_FILE, raise_on_failure=False)
    print("RESULT", result)
finally:
    remote.stop()
