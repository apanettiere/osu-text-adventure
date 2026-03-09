# The Dark Forest - osu-text-adventure

Python text adventure with a Pygame UI. The world is JSON-driven, movement is tile-based, and progression is item-gated.

## Quick Start

```bash
pip install pygame
cd src
python pygame_main.py
```

## Final Alpha Design

### Core objective
- Reach the lighthouse by collecting required tools and crossing blockers.

### Current room flow
- `clearing` -> start area with `machete` and `note`
- `thick_forest` (north) -> requires `machete`, contains `lantern`, `raft`, `climbing_gear`
- `riverbank` (south) -> cross to `far_shore` with `raft`
- `cave_entrance` (east) -> requires `lantern`, includes `old_map` and cave painting clue
- `mountain_pass` (west) -> requires `climbing_gear`, contains lighthouse endgame area

### Controls
- Movement: Arrow keys, or `go north/south/east/west` (shortcuts `n/s/e/w`)
- Actions: `look`, `examine <feature>`, `enter <feature>`, `take <item>`, `use <item>`, `read <item>`, `drop <item>`
- Resources: `gather wood`, `gather stone`, `gather food`
- UI: `M` map, `I` inventory, `ESC` close map/inventory or return to menu
- Save: `F5` or type `save`

### Save and reset
- Auto-save happens during play.
- Main menu includes:
  - `Continue Saved Game`
  - `New Game`
  - `Reset Save` (confirm press)

## Demo Path (Short)

1. `take note`, `read note`, `take machete`
2. Go north, `enter cabin`, take `lantern`, `raft`, `climbing_gear`
3. Go east to cave with lantern, examine flat stone for painting/map clue
4. Go south to riverbank and cross with raft
5. Go west from clearing and enter mountain pass with climbing gear

## Project Structure

```text
src/pygame_main.py       # Pygame UI, map rendering, menu, save/load
src/engine/game_state.py # Game logic, room gating, hints, commands
src/engine/models.py     # Room and player models
src/engine/loader.py     # JSON loader and room map builder
src/engine/parser.py     # Natural-language command parser
data/game.json           # Current game design data
tests/                   # Automated tests
docs/                    # Alpha checklists and submission guides
```

## Running Tests

```bash
python -m pytest tests/ -v
```
