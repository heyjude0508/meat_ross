# Recompile all CitizenNPC blueprints after path fix (/Game/CitizenNPC junction).
import unreal

ROOT = "/Game/CitizenNPC"
FAILED = []
OK = []
SKIPPED = []


def log(msg):
    unreal.log(f"[CompileCitizenNPC] {msg}")


def compile_asset(path):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if not asset:
        FAILED.append((path, "load_asset returned None"))
        return
    try:
        if isinstance(asset, unreal.Blueprint):
            result = unreal.BlueprintEditorLibrary.compile_blueprint(asset)
            # compile_blueprint may return None; check generated class
            gen = asset.generated_class()
            if gen is None:
                FAILED.append((path, "generated_class is None after compile"))
            else:
                OK.append(path)
                unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=True)
        else:
            SKIPPED.append(path)
    except Exception as e:
        FAILED.append((path, str(e)))


def main():
    log("Listing assets...")
    paths = unreal.EditorAssetLibrary.list_assets(ROOT, recursive=True, include_folder=False)
    bp_paths = []
    for p in paths:
        # list_assets returns soft paths sometimes with .Name
        clean = p.split(".")[0]
        name = clean.split("/")[-1]
        if name.startswith("BP_") or name.startswith("ABP_") or name.startswith("WBP_"):
            bp_paths.append(clean)

    # Parent first: BP_Character, BP_master_female, BP_WatchBase, then children, then ABP
    priority = [
        "/Game/CitizenNPC/Character/Blueprints/BP_Character",
        "/Game/CitizenNPC/Character/Blueprints/BP_master_female",
        "/Game/CitizenNPC/CharacterParts/Blueprints/BP_WatchBase",
        "/Game/CitizenNPC/Character/Blueprints/BP_Character_dynamic",
        "/Game/CitizenNPC/CharacterParts/Animations/ABP_CitizenNPC_male",
        "/Game/CitizenNPC/CharacterParts/Animations/ABP_CitizenNPC_female",
    ]
    ordered = []
    for p in priority:
        if p in bp_paths:
            ordered.append(p)
            bp_paths.remove(p)
    ordered.extend(sorted(bp_paths))

    log(f"Compiling {len(ordered)} blueprints...")
    for i, path in enumerate(ordered, 1):
        log(f"[{i}/{len(ordered)}] {path}")
        compile_asset(path)

    unreal.EditorAssetLibrary.save_directory(ROOT, only_if_is_dirty=True, recursive=True)
    log(f"OK={len(OK)} FAILED={len(FAILED)} SKIPPED={len(SKIPPED)}")
    for path, err in FAILED:
        log(f"FAIL {path}: {err}")
    log("Done")


if __name__ == "__main__":
    main()
