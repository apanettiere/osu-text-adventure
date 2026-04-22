# Text Adventure Game Design

Andrew Panettiere

## Game Title

The Dark Forest

## Overview

The Dark Forest is a text-based survival adventure game written in Python with a Pygame UI. The player wakes up alone in a dark forest with no memory of how they arrived. The goal is to find help and escape by lighting the signal lantern at the top of an abandoned lighthouse on the far coast.

The game starts in one location with limited actions. As the player gathers resources, crafts basic tools, and finds gated items (machete, lantern, raft, climbing gear), new parts of the world open up. The world slowly expands as the player becomes stronger, from a forest clearing, into a deep forest, down to a riverbank, out across open water, and up a rocky pass to the lighthouse.

The game focuses on simple mechanics, clear progression, and clean structure. The player starts small and grows over time. The world feels limited at first and becomes larger as the player unlocks new areas.

## Core Gameplay

The player interacts with the game by typing short commands or using keyboard shortcuts.

### Commands

Examples:

* go north
* gather wood  *(or* g wood *)*
* inventory  *(or* i *)*
* look  *(or* l *)*
* enter cabin
* take raft
* craft spear
* use lantern
* dig

The parser reads the first word as the action and the second word as the target. Natural phrasing like "pick up raft", "look at rope post", or "go to cave" is normalised to the same verb set.

**Full verb list:**

look, go, gather, take, craft, examine, enter, drop, read, use, dig, combine, inventory, leave, exit, quit, help, hint.

**Shortcuts supported:**

| Input | Action |
|---|---|
| n / s / e / w | go north / south / east / west |
| Arrow keys | move one tile in that direction |
| l | look |
| i | inventory |
| g \<resource\> | gather \<resource\> |
| q | quit |
| M | open/close the map screen |
| F5 | save game |
| Esc | return to menu |

`leave` and `exit` (when used inside an `_interior` room) send the player back out the way they came in one step, so tight rooms like the cabin and shed feel snappy.

The game repeats a simple loop:

* show room description
* wait for player input
* process command
* update game state

## World Structure

### Rooms

The world is a single unified world map stitched together from three kinds of rooms:

* **Walkable overworld rooms** — traversed tile by tile, spawning at the opposite wall when entering from an exit direction.
* **Focused interior rooms** — one-room "focus" views centered on the screen, entered through a feature (`enter cabin`, `enter lighthouse`, etc.).
* **Water rooms** — raft-only zones drawn on top of procedural water (the bay and open ocean).

| Room | Size | Kind | Description |
|---|---|---|---|
| Forest Clearing | 17×17 | Walkable | Starting area. Central hub connecting all four compass directions. |
| Thick Forest | 19×13 | Walkable | North of clearing. Gated by machete. Contains the ranger's cabin. |
| Riverbank | 17×13 | Walkable | South of clearing. Has the tool shed and rope post. |
| Cave Entrance | 13×11 | Walkable (focus) | East of clearing. Gated by lantern. Leads to the cave chamber. |
| Cave Chamber | 13×9 | Focus | Deeper cave, reached through the cave tunnel. |
| Cabin Interior | 13×9 | Focus | Inside the cabin. Holds lantern, climbing gear, raft. |
| Tool Shed | 9×7 | Focus | Inside the shed at the riverbank. Holds the shovel. |
| Mountain Pass | 17×13 | Focus | West of clearing. Gated by climbing gear or by raft from the water side. |
| Lighthouse Interior | 15×11 | Focus | Inside the lighthouse. Contains the spiral stairs to the top. |
| Lantern Room | 17×11 | Focus | Top of the lighthouse. The signal lens and brazier live here. |
| River Run | 13×11 | Water | West arm of the river, flowing toward the mountain pass bay. |
| River Lake | 11×9 | Water | East arm of the river, widening into a lake. |
| Far Shore | 13×9 | Water | A muddy shore across the lake. Dead end on its own. |
| Open Waters | 36×52 | Water (transparent) | The bay west of the mountain pass. Holds four islands, one with buried treasure. |

Each walkable room is traversed tile by tile. The player moves one tile per step and exits only when reaching the edge wall in a direction that has an exit. When entering a room from a direction, the player spawns at the opposite wall's centre. When leaving a focused interior room back into the overworld, the player spawns directly next to the feature they entered through (e.g., leaving the cabin drops you just south of the cabin door).

### Gated Areas

Four routes are gated behind items:

| Route | Obstacle | Requirement |
|---|---|---|
| Clearing → Thick Forest | Bramble wall | Machete |
| Clearing → Cave Entrance | Darkness | Lantern |
| Clearing → Mountain Pass (land) | Cliff face | Climbing gear |
| Land → any water room | Fast-running water | Raft |

The mountain pass has two approaches: the cliff climb from the clearing (requires climbing gear) and the bay crossing from the water (requires raft). Either route unlocks the lighthouse.

### Room Features

Each room contains positioned features. Walking adjacent to a feature displays a short flavour description automatically. Features appear as labelled letters on the map and can be interacted with using `examine`, `enter`, `use`, or `read`.

**Forest Clearing:** stump (S), firepit (F), trail marker (T)

**Thick Forest:** cabin (C) — enters cabin interior, fallen tree (L)

**Riverbank:** rope post (P), flat rock (R), tool shed (D) — enters shed interior

**Cabin Interior:** loft ladder (L), bunk (B), worktable (T), door (D), fireplace (F), shelves (H), rug (U), storage chest (X), hanging herbs (Y)

**Cave Entrance:** flat stone (X), cave tunnel (U) — enters cave chamber

**Cave Chamber:** stone column (C), echo pool (O), chamber ledge (G)

**Tool Shed:** hook wall (H), broken shelf (S)

**Mountain Pass:** lighthouse (H) — enters lighthouse interior, cliff edge (E), tide pool (P)

**Lighthouse Interior:** spiral stairs (S) — enters lantern room, fogged window (W), maintenance locker (K), winch console (C)

**Lantern Room:** signal lens (L), signal brazier (B), shutter crank (C), signal lever (V), catwalk hatch (R)

**River Run:** flat rock (R)

**River Lake:** lake channel (H), jagged reef (J)

**Far Shore:** driftwood pile (W), reed bank (R)

**Open Waters:** north island (I), main island (M), X marks the spot (X), west isle (W)

### Room Data

All room data is loaded from a JSON file (`data/game.json`). Each room entry may contain:

* a description
* exits to other rooms
* gatherable resources
* entry requirements
* room dimensions (width, height)
* feature positions with label, description, and optional `enter_to` target
* loot items (some visible, some hidden until discovered)

## Map

The map is a single unified world revealed tile by tile as the player explores. The render has two modes:

* **Continuous overworld** — the forest, riverbank, river, bay, and cave entrance are drawn as one world grid. Obstacle art (`~~~` water, `###` bramble, `^^^` cliff, `|!|` deep woods) fills the gaps between regions.
* **Focused interior** — when the player enters the cabin, tool shed, cave chamber, lighthouse, or mountain pass, the view switches to a single-room focus centered on screen with its own background tint. Interior features and sprites are revealed immediately inside the room so the art is never hidden by fog.

Interior rooms that sit geometrically *inside* an overworld room (the cabin sits inside thick forest's bounds; the shed sits inside the riverbank) are layered carefully: in focus mode the interior wins tile ownership, so the cabin renders correctly; on the overworld the outer room wins, so the cabin exterior feature stays visible on the forest map.

### Fog of War

The map starts completely dark. As the player walks, a small radius of tiles around their position is permanently revealed. This means:

* You must physically walk through a room to see its interior.
* Features appear on the map only in areas you have already visited.
* Blocked areas appear as a dark silhouette with `?` once you attempt to enter them, but their interior is not revealed.
* Panoramic view unlocks after discovering the mountain pass or lighthouse, expanding what's visible on the map.

### Map Screen

Press **M** to open the full map screen. The map screen shows:

* The full revealed world in ASCII art.
* `@` at the player's exact tile position within the current room.
* Obstacle art (`~~~` river, `###` bramble, `^^^` cliff, `|!|` deep woods) in the corridor between rooms.
* Deep forest (`* ' ^ ,`) filling the space outside room boundaries, growing denser with distance.
* A raft icon on the bay once the raft is in inventory. A second raft travels with the player on the open waters.
* A warm lantern halo around `@` when the player carries a lantern in the cave.
* The last command sent, shown above the input bar.
* A blinking cursor in the input field.

The map screen is fully interactive. Arrow keys and typed commands work while the map is open. Press **M** again to return to the text log.

### Room Appearance

Rooms are drawn as ellipses using ASCII characters:

* `♦ * '` tree border for forest rooms (brighter for the current room)
* `. ,` ground texture inside
* `~ -` water border and `~ =` water floor for lake/river/ocean rooms
* `| +` plank-style edge and warm `. '` floor for the cabin interior
* `#` and `:` stone edge for cave rooms
* `^ |` cliff border for the mountain pass
* `# |` iron-bolt border for the lighthouse
* Faint silhouette for discovered-but-not-entered rooms

Exit openings in the treeline show as `.` gaps where paths connect.

## Resources and Items

The player can gather three resources:

* Wood — clearing, thick forest, far shore, open waters (driftwood from islands)
* Stone — clearing, riverbank, cave entrance, mountain pass
* Food — clearing, riverbank, river run, river lake, far shore, open waters

Resources are stored as counters in the player inventory.

### Items

| Item | Type | Source |
|---|---|---|
| Machete | Tool | Clearing loot |
| Lantern | Tool | Cabin interior loot |
| Climbing Gear | Tool | Cabin interior loot |
| Shovel | Tool | Tool shed loot |
| Raft | Crafted / staged | Cabin interior loot |
| Knife | Crafted | Recipe: 1 wood + 1 stone |
| Spear | Crafted | Recipe: 2 wood + 1 stone |
| Axe | Crafted | Recipe: 2 wood + 2 stone |
| Signal Flare | Tool | Buried on the main island (dig at X) |
| Note | Readable | Clearing loot |
| Old Map | Readable | Cave entrance loot |

### Crafting

`craft` opens the crafting flow, `craft list` shows recipes, and `craft <item>` attempts a specific recipe. Crafted outputs respect inventory weight: if the player is overencumbered, the craft still consumes inputs but drops the result in the current room for later pickup. The shortlist:

* **Knife** — 1 wood + 1 stone
* **Spear** — 2 wood + 1 stone
* **Axe** — 2 wood + 2 stone

## Win Condition

The player wins by lighting the signal at the top of the lighthouse.

The player must:

* gather wood and stone, craft a spear/axe/knife for confidence
* find the machete in the clearing
* enter the cabin in the thick forest for the lantern, climbing gear, and raft
* reach the mountain pass — either by climbing (climbing gear) or by water (raft across the bay)
* enter the lighthouse, climb the spiral stairs, and fire the signal (`use lantern`, `use torch`, `use lever`, `use brazier`, `light signal`, or similar verbs all work at the lantern room)

Optional side objective: the tool shed at the riverbank holds a shovel. Rafting west through the open waters, the player can `dig` at the X on the main island to uncover a signal flare.

When the signal fires, a rescue seaplane arrives and the game ends with an SOS victory screen.

## Technical Plan

The game uses:

* A two-word parser with natural-phrase normalisation and single-letter shortcuts (`n`, `s`, `e`, `w`, `l`, `i`, `g`, `q`)
* Arrow key movement mapped directly to go commands
* A JSON file to store all room, feature, and item data
* Classes for rooms and player state (`Room`, `Player`, `GameState`)
* Save/load support so a session can be resumed
* A main game loop to process user input
* Unit tests using pytest (211 passing)

### Project Structure

```
src/
  pygame_main.py      # Pygame UI, map renderer, menu, game loop
  engine/
    game_state.py     # Core logic, movement, gathering, commands, save/load
    models.py         # Room and Player classes
    loader.py         # JSON loading
    parser.py         # Command parsing and alias resolution
data/
  game.json           # All room definitions, features, items, recipes
tests/
  test_parser.py
  test_player.py
  test_gather_schema.py
  test_movement.py    # Intra-room movement, transitions, blocked rooms
  test_rooms.py       # Room dimensions, features, exits, gather
  test_items.py       # Items, raft/water rules, loot, crafting
  test_rendering.py   # Map-layer tile ownership, interior vs overworld
```

### UI

The Pygame window has three screens:

**Game screen:** Scrolling text log and a command input box at the bottom with a blinking cursor. Page Up / Page Down to scroll history.

**Map screen (M):** Full-window ASCII map of the revealed world. Input bar at the bottom shows the last command sent and accepts new commands. Hint text in the corner shows available controls. Interior rooms render as a centered focus view.

**Main menu:** Start Game, How to Play, Quit.

**How to Play screen:** Accessible from the main menu. Covers movement, gathering, the map, and all commands. Returns to menu with ESC, Enter, or Space.

The core game logic lives in the engine. The UI calls the engine and displays whatever output it returns. This separation makes it straightforward to add new screens or features without touching the game logic.
