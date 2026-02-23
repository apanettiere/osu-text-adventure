# Text Adventure Game Design  
Andrew Panettiere  

## Game Title  
The Dark Forest  

## Overview  

The Dark Forest is a simple text based survival adventure game written in Python. The player wakes up alone in a dark forest with no memory of how they arrived. The goal of the game is to find help and escape.

The game starts in one location with limited actions. As the player gathers resources and crafts basic tools, new parts of the forest become available.

The game focuses on simple mechanics, clear progression, and clean structure.

## Core Gameplay  

The player interacts with the game by typing short two word commands.

Examples:

- go north  
- gather wood  
- gather stone  
- craft torch  
- build fire  
- inventory  
- look  

The parser reads the first word as the action and the second word as the target.

The player can explore forest areas, collect resources, and craft items needed to progress.

## World Structure  

The world will include several connected areas:

- Forest Clearing  
- Thick Trees  
- River Bank  
- Abandoned Cabin  
- Deep Forest  
- Watchtower Trail  
- Old Watchtower  

Each area will be treated as a room. All room data will be loaded from a JSON file.

Some areas will be locked at first.

Examples:

- The Deep Forest requires a torch.  
- The Watchtower Trail requires a basic tool to clear debris.  

## Resources and Items  

The player can gather resources such as:

- Wood  
- Stone  
- Food  

The player can craft items such as:

- Fire  
- Torch  
- Basic tool  

Resources and crafted items will be stored in the player inventory.

## Win Condition  

The player wins by reaching an old watchtower deep in the forest and repairing it using gathered resources. After the player repairs the watchtower, they light a signal fire at the top. The signal alerts help, and the game ends.

## Technical Plan  

The game will use:

- A simple two word parser  
- A JSON file to store rooms and items  
- Classes for rooms and player state  
- A main game loop to process user input  

The project will start small and expand over time.