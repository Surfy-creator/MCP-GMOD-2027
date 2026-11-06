# Triggers, entity I/O and logic architecture

Contents: 1. Mental model · 2. Naming · 3. Patterns · 4. RP-specific logic · 5. Verification

## 1. Mental model
Entity I/O is an event graph: an **output** on entity A (`OnPressed`) fires an **input** on entity B (`Open`) after an optional delay, a limited number of times (refire). A map's logic is a directed graph; the goal is a graph a human can read, extend and debug. Use `io_graph` (MCP) to see it and `trigger_recipe` for vetted patterns. Output value format: `target,input,parameter,delay,refire` (comma in VMF; a 0x1B separator appears in some compiled BSPs).

## 2. Naming
`zone_role_id`: `bank_door_vault_01`, `bank_light_lobby_02`. Zone prefix first so wildcards work (`bank_light_*`) and sorting groups a building. One zone prefix per building/district. Never leave default names (`func_door_3`) on entities that are referenced.

## 3. Patterns
- **Relay hub**: trigger/button -> single `logic_relay` -> everything else. One edit point.
- **One-shot vs repeatable**: `trigger_once` vs `trigger_multiple` with `wait`; refire count 1 on single-use outputs.
- **Filters**: `filter_activator_name` / class filters on triggers instead of logic that checks the activator later.
- **Counters** (`math_counter`) for N-of-M objectives (heist terminals); `OnHitMax` opens the reward.
- **Doors + areaportals**: `func_areaportal` `target` = the door's targetname.
- **Delays on outputs** for sequencing; avoid long chains of `logic_timer`.
- **Teleports**: `trigger_teleport` -> `info_teleport_destination`; check destination clearance.

## 4. RP-specific logic
- Door ownership and jobs are configured on the server (DarkRP-style) and reference map door entities: keep door entities and names stable across map versions; do not turn a door into a different class without telling the server owner.
- Interiors: one vis cell per building (door + areaportal); the outdoor area is a shared cell.
- Spawns: `info_player_start` count >= expected peak; place near readable landmarks.
- Avoid physics-heavy contraptions in public spaces (server cost).

## 5. Verification
1. `vmf_analyze` / `io_graph`: zero broken connections and dangling `target`/`parentname` keys.
2. `rp_scorecard` before and after changes.
3. Compile with `-onlyents` for logic-only edits; test every button/trigger in game (`developer 1`, `ent_fire`).
