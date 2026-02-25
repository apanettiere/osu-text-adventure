# Text Adventure Game Design

Andrew Panettiere

## Game Title

The Dark Forest

## Overview

The Dark Forest is a simple text based survival adventure game written in Python. The player wakes up alone in a dark forest with no memory of how they arrived. The goal of the game is to find help and escape.

The game starts in one location with limited actions. At the beginning the player can only explore nearby areas and gather basic resources. As the player gathers resources and crafts basic tools, new parts of the forest become available. The world slowly expands as the player becomes stronger.

The game focuses on simple mechanics, clear progression, and clean structure. The player starts small and grows over time. The world feels limited at first and becomes larger as the player unlocks new areas.

## Core Gameplay

The player interacts with the game by typing short two word commands.

Examples:

* go north
* gather wood
* gather stone
* craft torch
* build fire
* inventory
* look

The parser reads the first word as the action and the second word as the target.

For example:

* go north moves the player north
* gather wood increases wood in the inventory
* craft torch creates a torch if the player has enough materials

The player can explore forest areas, collect resources, and craft items needed to progress. The game repeats a simple loop:

* show room description
* wait for player input
* process command
* update game state

## World Structure

The world will include several connected areas:

* Forest Clearing
* Thick Trees
* River Bank
* Abandoned Cabin
* Deep Forest
* Watchtower Trail
* Old Watchtower

Each area will be treated as a room. All room data will be loaded from a JSON file.

Each room may contain:

* a description
* exits to other rooms
* gatherable resources
* entry requirements

Some areas will be locked at first.

Examples:

* The Deep Forest requires a torch.
* The Watchtower Trail requires a basic tool to clear debris.
* The Watchtower requires materials before it can be repaired.

## Resources and Items

The player can gather resources such as:

* Wood
* Stone
* Food

Resources are stored as counters in the player inventory.

Example:

* wood 2
* stone 1
* food 3

The player can craft items such as:

* Fire
* Torch
* Basic tool

Crafting requires specific amounts of resources.

Example:

* Torch requires wood and fire
* Basic tool requires wood and stone

Resources and crafted items will be stored in the player inventory.

## Win Condition

The player wins by reaching an old watchtower deep in the forest and repairing it using gathered resources.

The player must:

* gather enough materials
* clear the path
* repair the structure
* light a signal fire

After the player repairs the watchtower, they light a signal fire at the top. The signal alerts help, and the game ends.

## Technical Plan

The game will use:

* A simple two word parser
* A JSON file to store rooms and items
* Classes for rooms and player state
* A main game loop to process user input
* Basic unit tests using pytest

The project will start small and expand over time.

### UI Plan (Pygame Foundation)

The project will use a pygame window as the primary interface. The UI will include a simple main menu and a game screen with a scrolling text log and a command input box. The core game logic will live in the engine, and the UI will display whatever output the engine returns. This will make it easier to add features later such as a map overlay and combat screens without rewriting the game logic.