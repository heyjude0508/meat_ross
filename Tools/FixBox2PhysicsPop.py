# Inspect and fix PIE physics "pop" on Office TestFiles > box_2 nested desk props.
# Children overlapping a solid parent/sibling with Simulate Physics ON get launched at BeginPlay.
import json
import os
import traceback

import unreal

REPORT_PATH = r"E:/game/design/Epic Games/project/meat_ross/Tools/_box2_physics_report.txt"
MAP_PATH = "/Game/Office/Maps/Office"
MAP_HINT = "Office"
INSPECT_ONLY = os.environ.get("FIX_BOX2_INSPECT_ONLY", "").strip() in ("1", "true", "True", "yes")
CHILD_NAME_HINTS = (
    "book_01",
    "folder_1",
    "folder_2",
    "folder_3",
    "folder_4",
    "manifold_01",
    "notebook",
    "paper_01",
    "papers",
    "paperbox",
    "paperpad",
    "paperpile",
    "fileholder",
    "manilla",
    "manifold",
)
NESTED_OVERLAP_FRACTION = 0.45
SURFACE_SLOP_UU = 2.0
SURFACE_MAX_AXIS_UU = 24.0


def log(msg):
    line = f"[FixBox2] {msg}"
    unreal.log(line)
    print(line)


def safe_get(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def safe_set(obj, name, value):
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception:
        return False


def enum_name(v):
    try:
        return str(v)
    except Exception:
        return repr(v)


def vec3(v):
    if v is None:
        return None
    try:
        return (round(float(v.x), 3), round(float(v.y), 3), round(float(v.z), 3))
    except Exception:
        return str(v)


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


def prims(actor):
    try:
        return list(actor.get_components_by_class(unreal.PrimitiveComponent) or [])
    except Exception:
        return []


def mesh_of(comp):
    try:
        sm = safe_get(comp, "static_mesh")
        if sm:
            return sm.get_path_name()
    except Exception:
        pass
    return ""


def attached_children(actor, recursive=True):
    kids = []
    try:
        raw = actor.get_attached_actors(True, recursive)
        kids = list(raw or [])
    except TypeError:
        try:
            raw = actor.get_attached_actors()
            kids = list(raw or [])
        except Exception:
            kids = []
    except Exception:
        kids = []
    if recursive and kids:
        # If the API didn't recurse, walk manually.
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
    return [k for k in kids if k]


def attach_parent(actor):
    for fn in ("get_attach_parent_actor", "get_parent_actor"):
        try:
            p = getattr(actor, fn)()
            if p:
                return p
        except Exception:
            pass
    try:
        rc = actor.root_component
        if rc:
            parent_comp = rc.get_attach_parent()
            if parent_comp:
                return parent_comp.get_owner()
    except Exception:
        pass
    return None


def aabb(actor, colliding_only=True):
    try:
        origin, extent = actor.get_actor_bounds(colliding_only, False)
        return origin, extent
    except TypeError:
        origin, extent = actor.get_actor_bounds(colliding_only)
        return origin, extent
    except Exception:
        loc = actor.get_actor_location()
        return loc, unreal.Vector(0, 0, 0)


def aabb_overlap_axes(a, b, colliding_only=True):
    oa, ea = aabb(a, colliding_only)
    ob, eb = aabb(b, colliding_only)
    ox = (float(ea.x) + float(eb.x)) - abs(float(oa.x) - float(ob.x))
    oy = (float(ea.y) + float(eb.y)) - abs(float(oa.y) - float(ob.y))
    oz = (float(ea.z) + float(eb.z)) - abs(float(oa.z) - float(ob.z))
    return ox, oy, oz, oa, ea, ob, eb


def is_aabb_overlap(a, b, slop=SURFACE_SLOP_UU):
    ox, oy, oz, _, _, _, _ = aabb_overlap_axes(a, b)
    return ox > slop and oy > slop and oz > slop


def child_volume(extent):
    return max(abs(float(extent.x) * float(extent.y) * float(extent.z) * 8.0), 1.0)


def overlap_fraction_of_child(a_child, b_other):
    ox, oy, oz, oa, ea, ob, eb = aabb_overlap_axes(a_child, b_other)
    if ox <= 0 or oy <= 0 or oz <= 0:
        return 0.0
    # Conservative AABB intersection size vs child AABB volume.
    ix = min(float(ea.x) * 2.0, ox)
    iy = min(float(ea.y) * 2.0, oy)
    iz = min(float(ea.z) * 2.0, oz)
    inter = max(ix, 0.0) * max(iy, 0.0) * max(iz, 0.0)
    return inter / child_volume(ea)


def name_matches_child(label):
    low = (label or "").lower()
    for hint in CHILD_NAME_HINTS:
        if hint.lower() in low:
            return True
    return False


def dump_comp(comp):
    info = {
        "name": comp.get_name(),
        "class": comp.get_class().get_name(),
        "mesh": mesh_of(comp),
        "mobility": enum_name(safe_get(comp, "mobility")),
        "simulate_physics": safe_get(comp, "simulate_physics"),
        "enable_gravity": safe_get(comp, "enable_gravity"),
        "collision_enabled": enum_name(safe_get(comp, "collision_enabled")),
        "collision_profile": str(safe_get(comp, "collision_profile_name") or ""),
        "generate_overlap_events": safe_get(comp, "generate_overlap_events"),
        "notify_rb_collision": safe_get(comp, "notify_rigid_body_collision"),
        "hidden_in_game": safe_get(comp, "hidden_in_game"),
        "visible": safe_get(comp, "visible"),
        "is_simulating_physics_fn": None,
        "body": {},
    }
    try:
        info["is_simulating_physics_fn"] = bool(comp.is_simulating_physics())
    except Exception:
        pass
    try:
        info["collision_enabled_fn"] = enum_name(comp.get_collision_enabled())
    except Exception:
        pass
    try:
        info["collision_profile_fn"] = str(comp.get_collision_profile_name())
    except Exception:
        pass
    bi = safe_get(comp, "body_instance")
    if bi:
        for p in (
            "simulate_physics",
            "enable_gravity",
            "collision_enabled",
            "collision_profile_name",
            "notify_rigid_body_collision",
            "use_ccd",
            "auto_weld",
            "start_awake",
            "linear_damping",
            "angular_damping",
        ):
            val = safe_get(bi, p)
            if val is not None:
                info["body"][p] = enum_name(val) if p in ("collision_enabled",) else (
                    str(val) if p == "collision_profile_name" else val
                )
    try:
        b = comp.bounds
        info["bounds_origin"] = vec3(b.origin)
        info["bounds_extent"] = vec3(b.box_extent)
    except Exception:
        pass
    mesh = safe_get(comp, "static_mesh")
    if mesh:
        try:
            bs = mesh.get_editor_property("body_setup")
            if bs:
                info["mesh_collision_trace_flag"] = enum_name(safe_get(bs, "collision_trace_flag"))
        except Exception:
            pass
    return info


def dump_actor(actor):
    loc = actor.get_actor_location()
    rot = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    origin, extent = aabb(actor, True)
    parent = attach_parent(actor)
    rel = None
    try:
        rc = actor.root_component
        if rc:
            rel = vec3(rc.relative_location)
    except Exception:
        pass
    info = {
        "label": actor_label(actor),
        "name": actor.get_name(),
        "class": actor.get_class().get_name(),
        "folder": folder_path(actor),
        "loc": vec3(loc),
        "rot": (round(float(rot.pitch), 2), round(float(rot.yaw), 2), round(float(rot.roll), 2)),
        "scale": vec3(scale),
        "rel_loc": rel,
        "attach_parent": actor_label(parent) if parent else None,
        "bounds_origin": vec3(origin),
        "bounds_extent": vec3(extent),
        "components": [dump_comp(c) for c in prims(actor)],
    }
    return info


def find_box2(actors):
    exact = []
    fuzzy = []
    for a in actors:
        lb = actor_label(a)
        low = lb.lower()
        if lb == "box_2" or a.get_name() == "box_2":
            exact.append(a)
        elif "box_2" in low:
            fuzzy.append(a)
    if exact:
        return exact[0], exact, fuzzy
    if fuzzy:
        return fuzzy[0], exact, fuzzy
    return None, exact, fuzzy


def collect_group(box, actors):
    group = []
    seen = set()

    def add(a, reason):
        if not a or id(a) in seen:
            return
        seen.add(id(a))
        group.append((a, reason))

    add(box, "root")
    for ch in attached_children(box, recursive=True):
        add(ch, "attached")

    box_id = id(box)
    for a in actors:
        if id(a) in seen:
            continue
        p = attach_parent(a)
        walk = p
        hops = 0
        while walk and hops < 8:
            if id(walk) == box_id:
                add(a, "attach_parent_chain")
                break
            walk = attach_parent(walk)
            hops += 1

    box_folder = folder_path(box)
    ox, ex = aabb(box, False)
    max_r = max(float(ex.x), float(ex.y), float(ex.z), 80.0) * 2.5 + 120.0
    for a in actors:
        if id(a) in seen:
            continue
        fp = folder_path(a).replace("\\", "/")
        fp_low = fp.lower()
        if "box_2" in fp_low.split("/"):
            add(a, "folder_under_box_2")
            continue
        if "TestFiles" in fp and is_aabb_overlap(a, box):
            add(a, "TestFiles+overlap_box")
            continue
        lb = actor_label(a)
        if not name_matches_child(lb):
            continue
        same_folder = ("TestFiles" in fp) or (box_folder and fp == box_folder)
        loc = a.get_actor_location()
        dist = ((float(loc.x) - float(ox.x)) ** 2 + (float(loc.y) - float(ox.y)) ** 2 + (float(loc.z) - float(ox.z)) ** 2) ** 0.5
        if same_folder or dist <= max_r:
            add(a, "name+proximity" if not same_folder else "name+TestFiles")
    return group


def any_simulate(actor):
    for c in prims(actor):
        if safe_get(c, "simulate_physics") is True:
            return True
        try:
            if c.is_simulating_physics():
                return True
        except Exception:
            pass
        bi = safe_get(c, "body_instance")
        if bi and safe_get(bi, "simulate_physics") is True:
            return True
    return False


def collision_blocks_physics(comp):
    ce = safe_get(comp, "collision_enabled")
    text = enum_name(ce).upper()
    return ("PHYSICS" in text) or ("QUERY_AND_PHYSICS" in text)


def disable_sim_on_actor(actor):
    changes = []
    for comp in prims(actor):
        before_sim = safe_get(comp, "simulate_physics")
        before_grav = safe_get(comp, "enable_gravity")
        before_mob = enum_name(safe_get(comp, "mobility"))
        did = False
        try:
            actor.modify()
            comp.modify()
        except Exception:
            pass
        try:
            comp.set_simulate_physics(False)
            did = True
        except Exception:
            pass
        if safe_set(comp, "simulate_physics", False):
            did = True
        bi = safe_get(comp, "body_instance")
        if bi and safe_set(bi, "simulate_physics", False):
            did = True
        if before_grav is True:
            try:
                comp.set_enable_gravity(False)
            except Exception:
                pass
            safe_set(comp, "enable_gravity", False)
            if bi:
                safe_set(bi, "enable_gravity", False)
        # Decorative nested props should stay put.
        try:
            if safe_get(comp, "mobility") != unreal.ComponentMobility.STATIC:
                if safe_set(comp, "mobility", unreal.ComponentMobility.STATIC):
                    did = True
        except Exception:
            pass
        after_sim = safe_get(comp, "simulate_physics")
        after_mob = enum_name(safe_get(comp, "mobility"))
        if did or before_sim is True or "MOVABLE" in (before_mob or "").upper():
            changes.append(
                f"{comp.get_name()} simulate {before_sim}->{after_sim} "
                f"gravity {before_grav}->{safe_get(comp, 'enable_gravity')} "
                f"mobility {before_mob}->{after_mob}"
            )
    return changes


def body_collision(comp):
    bi = safe_get(comp, "body_instance")
    if bi:
        ce = safe_get(bi, "collision_enabled")
        if ce is not None:
            return enum_name(ce)
    try:
        return enum_name(comp.get_collision_enabled())
    except Exception:
        return enum_name(safe_get(comp, "collision_enabled"))


def profile_name(comp):
    try:
        return str(comp.get_collision_profile_name() or "")
    except Exception:
        return str(safe_get(comp, "collision_profile_name") or "")


def set_query_only(actor):
    changes = []
    for comp in prims(actor):
        before = body_collision(comp)
        before_prof = profile_name(comp)
        if before and "NO_COLLISION" in before.upper():
            continue
        try:
            actor.modify()
            comp.modify()
        except Exception:
            pass
        try:
            comp.set_collision_profile_name("OverlapAll")
        except Exception:
            pass
        try:
            comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
        except Exception:
            pass
        safe_set(comp, "collision_enabled", unreal.CollisionEnabled.QUERY_ONLY)
        bi = safe_get(comp, "body_instance")
        if bi:
            safe_set(bi, "collision_enabled", unreal.CollisionEnabled.QUERY_ONLY)
            safe_set(bi, "collision_profile_name", "OverlapAll")
        after = body_collision(comp)
        after_prof = profile_name(comp)
        if before != after or before_prof != after_prof:
            changes.append(
                f"{comp.get_name()} collision {before}->{after} profile {before_prof}->{after_prof}"
            )
    return changes


def nudge_actor(actor, dx, dy, dz):
    loc = actor.get_actor_location()
    new = unreal.Vector(float(loc.x) + dx, float(loc.y) + dy, float(loc.z) + dz)
    try:
        actor.modify()
    except Exception:
        pass
    actor.set_actor_location(new, False, False)
    return vec3(loc), vec3(actor.get_actor_location())


def classify_overlap(child, other):
    ox, oy, oz, oa, ea, ob, eb = aabb_overlap_axes(child, other)
    overlapping = ox > SURFACE_SLOP_UU and oy > SURFACE_SLOP_UU and oz > SURFACE_SLOP_UU
    frac = overlap_fraction_of_child(child, other) if overlapping else 0.0
    nested = overlapping and frac >= NESTED_OVERLAP_FRACTION
    shallow = overlapping and (not nested) and min(ox, oy, oz) <= SURFACE_MAX_AXIS_UU
    return {
        "other": actor_label(other),
        "overlap_xyz": (round(ox, 2), round(oy, 2), round(oz, 2)),
        "fraction": round(frac, 3),
        "overlapping": overlapping,
        "nested": nested,
        "shallow": shallow,
    }


def current_world_name():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    return world.get_name() if world else "", world


def save_map():
    ok = False
    try:
        ok = bool(unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level())
    except Exception as e:
        log(f"save_current_level err: {e}")
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception as e:
        log(f"save_dirty_packages err: {e}")
    return ok


def write_report(text):
    try:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(text)
        log(f"Wrote report {REPORT_PATH}")
    except Exception as e:
        log(f"report write err: {e}")


def main():
    lines = []

    def both(msg):
        log(msg)
        lines.append(msg)

    world_name, world = current_world_name()
    both(f"world={world_name} path={world.get_path_name() if world else None}")
    if MAP_HINT.lower() not in (world_name or "").lower():
        both(f"Loading {MAP_PATH} (current world is {world_name!r})")
        try:
            unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        except Exception as e:
            both(f"ERROR: load_map failed: {e}")
            write_report("\n".join(lines) + "\n")
            return
        world_name, world = current_world_name()
        both(f"world={world_name} path={world.get_path_name() if world else None}")

    actors = all_level_actors()
    both(f"level_actors={len(actors)}")

    box, exact, fuzzy = find_box2(actors)
    both(f"box_2 exact={[actor_label(a) for a in exact]} fuzzy={[actor_label(a) for a in fuzzy]}")
    if not box:
        sample = []
        for a in actors:
            lb = actor_label(a)
            fp = folder_path(a)
            if "TestFiles" in fp or "box" in lb.lower() or name_matches_child(lb):
                sample.append(f"{lb}|{fp}|{a.get_class().get_name()}")
        both(f"ERROR: box_2 not found. sample={sample[:80]}")
        write_report("\n".join(lines) + "\n")
        return

    both(
        f"ROOT {actor_label(box)} class={box.get_class().get_name()} "
        f"folder={folder_path(box)!r} loc={vec3(box.get_actor_location())}"
    )
    testfiles = []
    wanted = ("book_01", "notebook_02", "paper_01", "manifold", "notebook_01")
    for a in actors:
        lb = actor_label(a)
        fp = folder_path(a)
        if "TestFiles" in fp:
            testfiles.append(f"{lb}|{fp}")
        low = lb.lower()
        if any(w in low for w in wanted):
            both(f"NAMED {lb} folder={fp!r} class={a.get_class().get_name()} loc={vec3(a.get_actor_location())}")
    both(f"TESTFILES_COUNT={len(testfiles)} TESTFILES={testfiles[:80]}")

    group = collect_group(box, actors)
    both(f"group_size={len(group)} members={[actor_label(a)+':'+r for a, r in group]}")

    dumps = []
    for actor, reason in group:
        info = dump_actor(actor)
        info["reason"] = reason
        dumps.append(info)
        both(
            f"DUMP {info['label']} reason={reason} class={info['class']} folder={info['folder']!r} "
            f"loc={info['loc']} rel={info['rel_loc']} parent={info['attach_parent']} "
            f"scale={info['scale']} bounds_o={info['bounds_origin']} bounds_e={info['bounds_extent']}"
        )
        for c in info["components"]:
            both(
                f"  COMP {c['name']} {c['class']} mesh={c['mesh']} mob={c['mobility']} "
                f"sim={c['simulate_physics']}/{c['is_simulating_physics_fn']} grav={c['enable_gravity']} "
                f"col={c['collision_enabled']} profile={c['collision_profile']} "
                f"overlap_ev={c['generate_overlap_events']} body={c['body']} "
                f"trace={c.get('mesh_collision_trace_flag')}"
            )

    # Overlaps among group (skip comparing an actor to itself).
    overlap_rows = []
    actors_only = [a for a, _ in group]
    for i, a in enumerate(actors_only):
        for b in actors_only[i + 1 :]:
            row_ab = classify_overlap(a, b)
            if row_ab["overlapping"]:
                row_ab["a"] = actor_label(a)
                row_ab["b"] = actor_label(b)
                overlap_rows.append(row_ab)
                both(
                    f"OVERLAP {row_ab['a']} vs {row_ab['b']} xyz={row_ab['overlap_xyz']} "
                    f"frac={row_ab['fraction']} nested={row_ab['nested']} shallow={row_ab['shallow']}"
                )
    if not overlap_rows:
        both("OVERLAP none among group AABBs (colliding components)")

    # Also test vs nearby world statics for the parent (desk/floor squeeze).
    nearby_hits = []
    box_origin, box_extent = aabb(box, True)
    reach = max(float(box_extent.x), float(box_extent.y), float(box_extent.z), 50.0) + 80.0
    group_ids = {id(a) for a in actors_only}
    for other in actors:
        if id(other) in group_ids:
            continue
        if other.get_class().get_name() not in ("StaticMeshActor", "StaticMeshActor"):
            cls = other.get_class().get_name()
            if "StaticMesh" not in cls and "Brush" not in cls and "Landscape" not in cls:
                continue
        oloc = other.get_actor_location()
        if abs(float(oloc.x) - float(box_origin.x)) > reach * 2:
            continue
        if abs(float(oloc.y) - float(box_origin.y)) > reach * 2:
            continue
        if abs(float(oloc.z) - float(box_origin.z)) > reach * 2:
            continue
        for member in actors_only:
            row = classify_overlap(member, other)
            if row["overlapping"]:
                nearby_hits.append((actor_label(member), actor_label(other), row))
                both(
                    f"WORLD_OVERLAP {actor_label(member)} vs {actor_label(other)} "
                    f"xyz={row['overlap_xyz']} frac={row['fraction']} nested={row['nested']} shallow={row['shallow']}"
                )
                break
    if not nearby_hits:
        both("WORLD_OVERLAP none nearby")

    nested_labels = set()
    shallow_pairs = []
    for row in overlap_rows:
        if row["nested"]:
            nested_labels.add(row["a"])
            nested_labels.add(row["b"])
        if row["shallow"]:
            shallow_pairs.append(row)

    # Root box itself is the container; children overlapping it are nested contents.
    for actor, _ in group:
        if actor == box:
            continue
        row = classify_overlap(actor, box)
        if row["overlapping"]:
            both(
                f"VS_PARENT {actor_label(actor)} xyz={row['overlap_xyz']} frac={row['fraction']} "
                f"nested={row['nested']} shallow={row['shallow']}"
            )
            if row["nested"] or row["fraction"] > 0.15:
                nested_labels.add(actor_label(actor))
            elif row["shallow"]:
                shallow_pairs.append({"a": actor_label(actor), "b": actor_label(box), **row})

    both(f"NESTED_CONTENTS {sorted(nested_labels)}")
    both(f"SHALLOW_PAIRS {[(p.get('a'), p.get('b'), p.get('overlap_xyz')) for p in shallow_pairs]}")

    changes = []
    if INSPECT_ONLY:
        both("INSPECT_ONLY=1 skipping simulate/collision/nudge/save")
        write_report("\n".join(lines) + "\n\nDUMPS_JSON\n" + json.dumps(dumps, indent=2, default=str) + "\n")
        both("Done")
        return

    # 1) Kill simulate physics on the whole decorative group. Nested desk clutter
    #    must not be rigid bodies while intersecting the file box / siblings.
    for actor, reason in group:
        sim_before = any_simulate(actor)
        mob_changes = disable_sim_on_actor(actor)
        sim_after = any_simulate(actor)
        if mob_changes or sim_before:
            msg = (
                f"FIX_SIM {actor_label(actor)} ({reason}) sim {sim_before}->{sim_after} "
                f"details={mob_changes}"
            )
            both(msg)
            changes.append(msg)

    # 2) Nested contents: QueryOnly so they still trace but cannot physically
    #    squeeze against the parent box if something else simulates.
    for actor, reason in group:
        if actor == box:
            continue
        lb = actor_label(actor)
        if lb in nested_labels or reason.startswith("attached") or name_matches_child(lb):
            # Treat attached / named nested office props as decorative contents.
            col_changes = set_query_only(actor)
            if col_changes:
                msg = f"FIX_COL {lb} {col_changes}"
                both(msg)
                changes.append(msg)

    # 3) Shallow surface penetration: nudge the smaller/child actor along +Z
    #    (and MTV if Z isn't the minimum axis) so they aren't squeezed.
    label_to_actor = {actor_label(a): a for a, _ in group}
    nudged = set()
    for pair in shallow_pairs:
        a_name = pair.get("a")
        b_name = pair.get("b")
        a = label_to_actor.get(a_name)
        b = label_to_actor.get(b_name)
        if not a or not b:
            continue
        if a == box:
            child, other = b, a
        elif b == box:
            child, other = a, b
        else:
            # Nudge the smaller one.
            _, ea = aabb(a, True)
            _, eb = aabb(b, True)
            child, other = (a, b) if child_volume(ea) <= child_volume(eb) else (b, a)
        cl = actor_label(child)
        if cl in nested_labels or cl in nudged:
            continue
        ox, oy, oz, oa, ea, ob, eb = aabb_overlap_axes(child, other)
        dx = dy = dz = 0.0
        loc = child.get_actor_location()
        # A prior +Z nudge can float a side-by-side desk prop up through a tall
        # neighbor AABB. Restore papers to the original desk height if that happened.
        if cl == "papers" and float(loc.z) > 106.0:
            dz = 104.0 - float(loc.z)
        # Side-by-side clutter: move away on the smallest horizontal overlap.
        # Only lift when the child center is already above the other actor.
        child_above = float(oa.z) >= float(ob.z)
        if child_above and oz <= min(ox, oy) and oz <= SURFACE_MAX_AXIS_UU and abs(dz) < 0.01:
            dz = oz + 1.0
        else:
            if ox <= oy:
                dx = (ox + 1.0) if float(oa.x) >= float(ob.x) else -(ox + 1.0)
            else:
                dy = (oy + 1.0) if float(oa.y) >= float(ob.y) else -(oy + 1.0)
        before, after = nudge_actor(child, dx, dy, dz)
        nudged.add(cl)
        msg = f"FIX_XFORM {cl} {before} -> {after} delta=({dx:.2f},{dy:.2f},{dz:.2f}) vs {actor_label(other)}"
        both(msg)
        changes.append(msg)

    if not changes:
        both("NO_CHANGES (already non-simulating / no actionable overlap)")

    # Verify after
    both("--- AFTER ---")
    for actor, reason in group:
        info = dump_actor(actor)
        both(
            f"AFTER {info['label']} loc={info['loc']} rel={info['rel_loc']} parent={info['attach_parent']}"
        )
        for c in info["components"]:
            both(
                f"  COMP {c['name']} sim={c['simulate_physics']}/{c['is_simulating_physics_fn']} "
                f"grav={c['enable_gravity']} mob={c['mobility']} col={c['collision_enabled']} "
                f"col_fn={c.get('collision_enabled_fn')} profile={c['collision_profile']} "
                f"body={c['body']}"
            )

    ok = save_map()
    both(f"SAVE level_ok={ok}")
    both(f"CHANGE_COUNT={len(changes)}")
    write_report("\n".join(lines) + "\n\nDUMPS_JSON\n" + json.dumps(dumps, indent=2, default=str) + "\n")
    both("Done")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log(traceback.format_exc())
        raise
