# Text Adventure Game Design

Andrew Panettiere

## Game Title

The Dark Forest

## Overview

The Dark Forest is a text-based survival adventure game written in Python with a Pygame UI. The player wakes up alone in a dark forest with no memory of how they arrived. The goal is to find help and escape.

The game starts in one location with limited actions. As the player gathers resources and crafts basic tools, new parts of the forest become available. The world slowly expands as the player becomes stronger.

The game focuses on simple mechanics, clear progression, and clean structure. The player starts small and grows over time. The world feels limited at first and becomes larger as the player unlocks new areas.

## Core Gameplay

The player interacts with the game by typing short commands or using keyboard shortcuts.

### Commands

Examples:

* go north
* gather wood  *(or* g wood *)*
* inventory  *(or* i *)*
* look  *(or* l *)*

The parser reads the first word as the action and the second word as the target.

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

The player can explore forest areas, collect resources, and craft items needed to progress. The game repeats a simple loop:

* show room description
* wait for player input
* process command
* update game state

## World Structure

### Rooms

The world contains five main walkable rooms connected on a single unified map:

| Room | Size | Description |
|---|---|---|
| Forest Clearing | 9×9 | Starting area. Central hub. |
| Shadow Trees | 11×7 | North of clearing. Dense forest. |
| Soggy Path | 7×11 | South of clearing. Muddy trail toward the river. |
| Stone Foothills | 9×7 | East of clearing. Rocky ground, rising wind. |
| Fallen Pines | 9×7 | West of clearing. Downed trees, old lantern. |

Each main room is walkable tile-by-tile. The player moves one tile per step and exits only when reaching the edge wall in a direction that has an exit. When entering a room from a direction, the player spawns at the opposite wall's centre.

### Blocked Areas

Beyond the five main rooms, four areas are locked behind obstacles. These are shown on the map but cannot be entered without the required item:

| Area | Obstacle | Requirement |
|---|---|---|
| Bramble Wall | Brambles north of Shadow Trees | Machete |
| Rushing River | River south of Soggy Path | Raft |
| Black Cliffline | Cliff east of Stone Foothills | Climbing gear |
| Deep Woods | Dense forest west of Fallen Pines | Axe |

Obstacle art is drawn on the map in the corridor between the main room and the blocked area so the player can see what is blocking them before they attempt to enter.

### Room Features

Each walkable room contains positioned features. Walking adjacent to a feature displays a short flavour description automatically. Features also appear as labelled markers on the map.

**Forest Clearing:** Stone well (W), animal tracks (T), fire ash (F)

**Shadow Trees:** Mossy boulder (B), claw scratch marks (S)

**Soggy Path:** Gnarled root (R), rusted tin cup (C)

**Stone Foothills:** Split lightning boulder (B), worn inscription (I)

**Fallen Pines:** Rusted lantern (L), log pile (P)

### Room Data

All room data is loaded from a JSON file (`data/game.json`). Each room entry may contain:

* a description
* exits to other rooms
* gatherable resources
* entry requirements
* room dimensions (width, height)
* feature positions with label and description

## Map

The map is a single unified world revealed tile by tile as the player explores.

### Fog of War

The map starts completely dark. As the player walks, a small radius of tiles around their position is permanently revealed. This means:

* You must physically walk through a room to see its interior.
* Features appear on the map only in areas you have already visited.
* Blocked areas appear as a dark silhouette with `?` once you attempt to enter them, but their interior is not revealed.

### Map Screen

Press **M** to open the full map screen. The map screen shows:

* The full revealed world in ASCII art.
* `@` at the player's exact tile position within the current room.
* Obstacle art (`~~~` river, `###` bramble, `^^^` cliff, `|!|` deep woods) in the corridor between rooms.
* Deep forest (`* ' ^ ,`) filling the space outside room boundaries, growing denser with distance.
* The last command sent, shown above the input bar.
* A blinking cursor in the input field.

The map screen is fully interactive. Arrow keys and typed commands work while the map is open. Press **M** again to return to the text log.

### Room Appearance

Rooms are drawn as ellipses using ASCII characters:

* `♦ * '` tree border for explored rooms (brighter for the current room)
* `. ,` ground texture inside
* Faint silhouette for discovered-but-not-entered rooms
* `#` and `x` bramble border for blocked rooms

Exit openings in the treeline show as `.` gaps where paths connect.

## Resources and Items

The player can gather resources in rooms that support them:

* Wood
* Stone
* Food

Resources are stored as counters in the player inventory.

The player can craft items such as:

* Fire
* Torch
* Basic tool

Crafting requires specific amounts of resources.

Example:

* Torch requires wood and fire
* Basic tool requires wood and stone

Resources and crafted items are stored in the player inventory.

## Win Condition

The player wins by reaching an old watchtower deep in the forest and repairing it using gathered resources.

The player must:

* gather enough materials
* clear each blocked path using crafted items
* reach the watchtower
* repair the structure
* light a signal fire

After the player repairs the watchtower they light a signal fire at the top. The signal alerts help and the game ends.

## Technical Plan

The game uses:

* A two-word parser with single-letter shortcuts (`n`, `s`, `e`, `w`, `l`, `i`, `g`, `q`)
* Arrow key movement mapped directly to go commands
* A JSON file to store all room and item data
* Classes for rooms and player state (`Room`, `Player`, `GameState`)
* A main game loop to process user input
* Unit tests using pytest

### Project Structure

```
src/
  pygame_main.py      # Pygame UI, map renderer, menu, game loop
  engine/
    game_state.py     # Core logic, movement, gathering, commands
    models.py         # Room and Player classes
    loader.py         # JSON loading
    parser.py         # Command parsing and alias resolution
data/
  game.json           # All room definitions, features, requirements
tests/
  test_parser.py
  test_player.py
  test_gather_schema.py
  test_movement.py    # Intra-room movement, transitions, blocked rooms
  test_rooms.py       # Room dimensions, features, exits, gather
```

### UI

The Pygame window has two screens:

**Game screen:** Scrolling text log and a command input box at the bottom with a blinking cursor. Page Up / Page Down to scroll history.

**Map screen (M):** Full-window ASCII map of the revealed world. Input bar at the bottom shows the last command sent and accepts new commands. Hint text in the corner shows available controls.

**Main menu:** Start Game, How to Play, Quit.

**How to Play screen:** Accessible from the main menu. Covers movement, gathering, the map, and all commands. Returns to menu with ESC, Enter, or Space.

The core game logic lives in the engine. The UI calls the engine and displays whatever output it returns. This separation makes it straightforward to add new screens or features without touching the game logic.