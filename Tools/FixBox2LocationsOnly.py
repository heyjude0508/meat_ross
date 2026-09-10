# Resolve box_2 TestFiles physics pop by LOCATION only.
# Do NOT disable Simulate Physics / do NOT change collision mode.
import json
import os
import traceback

import unreal

REPORT_PATH = r"E:/game/design/Epic Games/project/meat_ross/Tools/_box2_location_report.txt"
MAP_PATH = "/Game/Office/Maps/Office"
GAP_UU = 1.5  # clearance between collision AABBs
MAX_ITERS = 12


def log(msg):
    line = f"[FixBox2Loc] {msg}"
    unreal.log(line)
    print(line)


def safe_get(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def actor_label(actor):
    try:
        return actor.get_actor_label()
    except Exception:
        return actor.get_name()


def folder_path(actor):
    try:
        return str(actor.get_folder_path() or "")
    except Exception:
        return ""


def all_level_actors():
    try:
        return list(unreal.EditorLevelLibrary.get_all_level_actors() or [])
    except Exception:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        return list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) or [])


def attached_children(actor):
    kids = []
    try:
        kids = list(actor.get_attached_actors(True, True) or [])
    except TypeError:
        try:
            kids = list(actor.get_attached_actors() or [])
        except Exception:
            kids = []
    except Exception:
        kids = []
    # Manual recurse if needed
    seen = {id(k) for k in kids}
    stack = list(kids)
    while stack:
        cur = stack.pop()
        try:
            more = list(cur.get_attached_actors() or [])
        except Exception:
            more = []
        for m in more:
            if id(m) in seen:
                continue
            seen.add(id(m))
            kids.append(m)
            stack.append(m)
    return kids


def aabb(actor, colliding_only=True):
    try:
        origin, extent = actor.get_actor_bounds(colliding_only, False)
        return origin, extent
    except TypeError:
        return actor.get_actor_bounds(colliding_only)
    except Exception:
        loc = actor.get_actor_location()
        return loc, unreal.Vector(0, 0, 0)


def overlap_axes(a, b, colliding_only=True):
    oa, ea = aabb(a, colliding_only)
    ob, eb = aabb(b, colliding_only)
    ox = (float(ea.x) + float(eb.x)) - abs(float(oa.x) - float(ob.x))
    oy = (float(ea.y) + float(eb.y)) - abs(float(oa.y) - float(ob.y))
    oz = (float(ea.z) + float(eb.z)) - abs(float(oa.z) - float(ob.z))
    return ox, oy, oz, oa, ea, ob, eb


def is_overlap(a, b, slop=0.25):
    ox, oy, oz, *_ = overlap_axes(a, b)
    return ox > slop and oy > slop and oz > slop


def set_loc(actor, x, y, z):
    try:
        actor.modify()
    except Exception:
        pass
    actor.set_actor_location(unreal.Vector(float(x), float(y), float(z)), False, False)


def volume(extent):
    return max(abs(float(extent.x) * float(extent.y) * float(extent.z) * 8.0), 1.0)


def find_box2(actors):
    for a in actors:
        if actor_label(a) == "box_2" or a.get_name() == "box_2":
            return a
    for a in actors:
        if "box_2" in actor_label(a).lower():
            return a
    return None


def collect_group(box, actors):
    group = [box]
    seen = {id(box)}
    for ch in attached_children(box):
        if id(ch) not in seen:
            seen.add(id(ch))
            group.append(ch)
    for a in actors:
        if id(a) in seen:
            continue
        if folder_path(a) == "TestFiles" and a.get_class().get_name() == "StaticMeshActor":
            seen.add(id(a))
            group.append(a)
    return group


def dump_state(actors_only, tag):
    rows = []
    for a in actors_only:
        o, e = aabb(a, True)
        loc = a.get_actor_location()
        rows.append(
            f"{tag} {actor_label(a)} loc=({loc.x:.3f},{loc.y:.3f},{loc.z:.3f}) "
            f"bounds_o=({o.x:.3f},{o.y:.3f},{o.z:.3f}) "
            f"bounds_e=({e.x:.3f},{e.y:.3f},{e.z:.3f})"
        )
    return rows


def separate_pair(child, other, prefer_stack=True):
    """Move child so AABBs no longer overlap. Returns delta (dx,dy,dz) or None."""
    if not is_overlap(child, other):
        return None
    ox, oy, oz, oa, ea, ob, eb = overlap_axes(child, other)
    loc = child.get_actor_location()

    # Prefer stacking (+Z) when child is already mostly above, or thin paper-like.
    thin = float(ea.z) <= 4.0
    child_above = float(oa.z) >= float(ob.z) - 0.5
    if prefer_stack and (child_above or thin) and oz <= max(ox, oy) + 8.0:
        # Place child's bottom just above other's top + gap
        other_top = float(ob.z) + float(eb.z)
        child_half_z = float(ea.z)
        # Current bottom = origin.z - extent.z; we want bottom = other_top + GAP
        # Actor location may not equal bounds origin; shift by delta of origins.
        target_origin_z = other_top + GAP_UU + child_half_z
        dz = target_origin_z - float(oa.z)
        set_loc(child, loc.x, loc.y, float(loc.z) + dz)
        return (0.0, 0.0, dz)

    # Else separate on smallest horizontal axis (keep Z)
    if ox <= oy:
        dx = (ox + GAP_UU) if float(oa.x) >= float(ob.x) else -(ox + GAP_UU)
        set_loc(child, float(loc.x) + dx, loc.y, loc.z)
        return (dx, 0.0, 0.0)
    dy = (oy + GAP_UU) if float(oa.y) >= float(ob.y) else -(oy + GAP_UU)
    set_loc(child, loc.x, float(loc.y) + dy, loc.z)
    return (0.0, dy, 0.0)


def resolve_vs_parent(child, box):
    """If child is buried in solid parent AABB, lift onto parent top (or push out)."""
    if not is_overlap(child, box):
        return None
    ox, oy, oz, oa, ea, ob, eb = overlap_axes(child, box)
    loc = child.get_actor_location()
    # Deep nesting: lift to sit on box lid / top surface
    frac_z = oz / max(float(ea.z) * 2.0, 1.0)
    if frac_z > 0.35 or (ox > 2 and oy > 2 and oz > 2):
        box_top = float(ob.z) + float(eb.z)
        target_origin_z = box_top + GAP_UU + float(ea.z)
        dz = target_origin_z - float(oa.z)
        set_loc(child, loc.x, loc.y, float(loc.z) + dz)
        return (0.0, 0.0, dz)
    return separate_pair(child, box, prefer_stack=True)


def save_map():
    ok = False
    try:
        ok = bool(unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level())
    except Exception as e:
        log(f"save_current_level err: {e}")
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception as e:
        log(f"save_dirty err: {e}")
    return ok


def main():
    lines = []

    def both(msg):
        log(msg)
        lines.append(msg)

    # Load Office if needed
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    wname = world.get_name() if world else ""
    both(f"world={wname}")
    if "office" not in wname.lower():
        both(f"Loading {MAP_PATH}")
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        both(f"world={world.get_name() if world else None}")

    actors = all_level_actors()
    box = find_box2(actors)
    if not box:
        both("ERROR: box_2 not found")
        open(REPORT_PATH, "w", encoding="utf-8").write("\n".join(lines))
        return

    group = collect_group(box, actors)
    both(f"group={[actor_label(a) for a in group]}")
    for r in dump_state(group, "BEFORE"):
        both(r)

    # Do NOT touch simulate / collision profile — location only.
    movable = [a for a in group if a != box]
    changes = []

    for it in range(MAX_ITERS):
        moved = 0
        # 1) Resolve each child vs parent box
        for child in movable:
            delta = resolve_vs_parent(child, box)
            if delta:
                moved += 1
                msg = f"ITER{it} VS_PARENT {actor_label(child)} delta={tuple(round(v, 3) for v in delta)}"
                both(msg)
                changes.append(msg)

        # 2) Resolve sibling overlaps: move the higher / thinner one
        for i, a in enumerate(movable):
            for b in movable[i + 1 :]:
                if not is_overlap(a, b):
                    continue
                oa, ea = aabb(a, True)
                ob, eb = aabb(b, True)
                # Move the one with higher center (or thinner)
                if float(oa.z) > float(ob.z) + 0.01:
                    child, other = a, b
                elif float(ob.z) > float(oa.z) + 0.01:
                    child, other = b, a
                else:
                    child, other = (a, b) if float(ea.z) <= float(eb.z) else (b, a)
                # Prefer stack for paper-like pairs
                prefer = float(aabb(child, True)[1].z) <= 4.0
                delta = separate_pair(child, other, prefer_stack=prefer)
                if delta:
                    moved += 1
                    msg = (
                        f"ITER{it} SIBLING {actor_label(child)} vs {actor_label(other)} "
                        f"delta={tuple(round(v, 3) for v in delta)}"
                    )
                    both(msg)
                    changes.append(msg)
        if moved == 0:
            both(f"ITER{it} stable")
            break
    else:
        both("WARN: hit MAX_ITERS with remaining overlaps")

    # Report remaining overlaps
    remain = []
    for i, a in enumerate(group):
        for b in group[i + 1 :]:
            if is_overlap(a, b):
                ox, oy, oz, *_ = overlap_axes(a, b)
                remain.append((actor_label(a), actor_label(b), (round(ox, 2), round(oy, 2), round(oz, 2))))
                both(f"REMAIN_OVERLAP {actor_label(a)} vs {actor_label(b)} xyz={(round(ox,2), round(oy,2), round(oz,2))}")
    if not remain:
        both("REMAIN_OVERLAP none")

    for r in dump_state(group, "AFTER"):
        both(r)

    # Verify we did not flip simulate flags (read-only check)
    for a in group:
        for c in a.get_components_by_class(unreal.PrimitiveComponent) or []:
            bi = safe_get(c, "body_instance")
            sim = safe_get(bi, "simulate_physics") if bi else safe_get(c, "simulate_physics")
            both(f"SIM_CHECK {actor_label(a)} sim={sim}")

    ok = save_map()
    both(f"SAVE level_ok={ok} CHANGE_COUNT={len(changes)}")
    both("Done")
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log(traceback.format_exc())
        raise
