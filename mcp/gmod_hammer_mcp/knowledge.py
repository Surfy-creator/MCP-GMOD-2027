"""Curated, hand-written trigger/logic recipes and mapping rules (no copied Valve text)."""

RECIPES = {
    "button_door": {
        "purpose": "Button opens a door, optionally auto-closes; door area is culled with an areaportal.",
        "entities": [
            {"classname": "func_button", "targetname": "bank_btn_vault", "keys": {"spawnflags": "1025", "wait": "3"},
             "outputs": [["OnPressed", "bank_door_vault", "Open", "", "0", "-1"]]},
            {"classname": "func_door", "targetname": "bank_door_vault", "keys": {"speed": "100", "lip": "4", "wait": "3"},
             "outputs": [["OnFullyClosed", "bank_btn_vault", "Unlock", "", "0", "-1"]]},
            {"classname": "func_areaportal", "keys": {"target": "bank_door_vault", "StartOpen": "0"}},
        ],
        "notes": ["Name by zone_role_id (bank_door_vault) so wildcards like bank_* work.",
                  "func_areaportal 'target' must be the door's targetname so the portal opens/closes with it.",
                  "In RP maps keep door names/ids stable between map versions: server-side door ownership configs reference them."],
    },
    "one_shot_event": {
        "purpose": "Player enters a zone once: fire a relay that fans out to everything (alarm, lights, sound).",
        "entities": [
            {"classname": "trigger_once", "targetname": "bank_trg_alarm", "keys": {"spawnflags": "1"},
             "outputs": [["OnStartTouch", "bank_relay_alarm", "Trigger", "", "0", "-1"]]},
            {"classname": "logic_relay", "targetname": "bank_relay_alarm", "keys": {},
             "outputs": [["OnTrigger", "bank_snd_alarm", "PlaySound", "", "0", "-1"],
                         ["OnTrigger", "bank_light_*", "TurnOn", "", "0.1", "-1"],
                         ["OnTrigger", "bank_relay_alarm", "Disable", "", "0", "1"]]},
        ],
        "notes": ["Single entry point (the relay) = one place to edit later; avoids trigger -> N entities spaghetti.",
                  "trigger_once removes itself; use trigger_multiple + wait for repeatable."],
    },
    "filtered_zone": {
        "purpose": "Trigger reacting only to a specific named entity (e.g. a vehicle or a prop).",
        "entities": [
            {"classname": "filter_activator_name", "targetname": "flt_police_car", "keys": {"filtername": "police_car_1"}},
            {"classname": "trigger_multiple", "targetname": "garage_trg_enter", "keys": {"spawnflags": "1", "filtername": "flt_police_car", "wait": "1"},
             "outputs": [["OnStartTouch", "garage_door", "Open", "", "0", "-1"]]},
        ],
        "notes": ["Players are 'clients' (spawnflag 1); to react to props enable 'physics objects' (spawnflag 8) instead."],
    },
    "counter_puzzle": {
        "purpose": "Open something after N things happen (heist: 3 terminals hacked).",
        "entities": [
            {"classname": "math_counter", "targetname": "heist_cnt_terminals", "keys": {"min": "0", "max": "3"},
             "outputs": [["OnHitMax", "heist_door_vault", "Open", "", "0", "-1"]]},
            {"classname": "func_button", "targetname": "heist_btn_term_1", "keys": {"spawnflags": "1025"},
             "outputs": [["OnPressed", "heist_cnt_terminals", "Add", "1", "0", "1"]]},
        ],
        "notes": ["Give each button refire count 1 so it cannot be spammed.", "Duplicate button per terminal with its own name."],
    },
    "teleporter": {
        "purpose": "Teleport from a trigger to a destination (interior loading, sewer exits).",
        "entities": [
            {"classname": "trigger_teleport", "targetname": "sewer_trg_up", "keys": {"spawnflags": "1", "target": "sewer_dest_street"}},
            {"classname": "info_teleport_destination", "targetname": "sewer_dest_street", "keys": {}},
        ],
        "notes": ["Destination angles define player facing.", "Keep destination clear of solids; test with noclip off."],
    },
    "timed_sequence": {
        "purpose": "Chain actions with delays using the output delay field instead of logic_timer.",
        "entities": [
            {"classname": "logic_relay", "targetname": "show_relay", "keys": {},
             "outputs": [["OnTrigger", "show_fade", "Fade", "", "0", "-1"],
                         ["OnTrigger", "show_door", "Open", "", "2", "-1"],
                         ["OnTrigger", "show_snd", "PlaySound", "", "2.5", "-1"]]},
        ],
        "notes": ["Output format is: target,input,parameter,delay,refire-count."],
    },
}

RULES = {
    "naming": "zone_role_id (bank_door_vault_01). Prefix = zone, so wildcards (bank_light_*) work and the map stays navigable.",
    "io_hygiene": [
        "Funnel multi-effect events through a logic_relay.",
        "Never leave outputs pointing at deleted names; run vmf_analyze/io_graph before compiling.",
        "Use !self/!activator/!caller instead of extra named entities when possible.",
        "Prefer refire counts of 1 on one-shot outputs so they don't leak work at runtime.",
        "Avoid delays >= 30 s on gameplay-critical chains; use logic_timer with explicit enable/disable.",
    ],
    "optimization_order": [
        "1. Structure vs detail: only walls/floors/ceilings that seal space stay world brushes; everything else func_detail.",
        "2. Areaportals in every door/window frame that separates rooms; hint/skip only where vvis stats show long sightlines.",
        "3. prop_static for anything that never moves; prop_dynamic only for animated models; avoid prop_physics unless gameplay needs it.",
        "4. One env_cubemap per distinct reflective space; build cubemaps last, never rename the BSP afterwards.",
        "5. Lightmap scale 16 for most surfaces; 32-64 for large floors/roads; 8 only where shadows matter.",
        "6. Large outdoor RP maps: 3D skybox (sky_camera) for distant skyline instead of real geometry.",
        "7. Pack only custom content into the BSP (bspzip/-repack) or ship via Workshop addon; check pak size.",
    ],
    "rp_city_structure": [
        "Grid of blocks around a readable road spine; landmark per district for orientation.",
        "Each interior is its own vis cell (door + areaportal). Exteriors share one big open cell.",
        "Doors on named entities, one zone prefix per building; spawn/job points near readable landmarks.",
        "Keep interiors on a separate Hammer visgroup per building so teams can edit in parallel.",
        "Use instances (func_instance) for repeated building shells to keep the VMF small.",
    ],
    "hammerpp_workflow": [
        "Use Hammer++ x64 from GarrysMod/bin/win64 with game config pointing to garrysmod.fgd (+ hammerplusplus_fgd.fgd extensions).",
        "Compile from Hammer++ compile window (it runs vbsp/vvis/vrad from bin/win64) or via compile_plan for scripted builds.",
        "Use visgroups + autosave (Hammer++ writes *.vmf_autosave) and keep VMF in sourcesdk_content/garrysmod/mapsrc.",
        "Prefabs live in bin/win64/Prefabs; instances preferred for repeated shells.",
        "Hot reload of models/materials in Hammer++ speeds up prop iteration.",
    ],
}
