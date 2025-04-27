# Increment Name - Blender Addon

A Blender addon that properly increments numbered object and collection names after duplication.

## Features

- **Intelligent Number Incrementing**: Finds and increments the first number in object names after duplication.
- **Escape Patterns**: Define patterns to exclude certain numbers from being incremented.
- **Object Duplication**: Press Shift+D in Object Mode to duplicate objects with automatic name incrementing.
- **Collection Duplication**: Press Shift+D in the Outliner to duplicate collections with automatic name incrementing.
- **Recursive Collection Support**: Option to rename objects in nested collections during duplication.

## Installation

1. Download the [latest release](https://github.com/PatrickKang/blender-increment-name/releases).
2. In Blender, go to Edit > Preferences > Add-ons.
3. Click "Install..." and select the downloaded zip file.
4. Enable the addon by checking the box next to "Object: Increment Name".

## Usage

### Object Duplication
Simply press Shift+D in Object Mode to duplicate objects with smart naming. The addon will automatically increment the first number in the name.

### Collection Duplication
Press Shift+D in the Outliner to duplicate collections. All objects within the collection will have their names incremented properly.

### Escape Patterns
You can define patterns to exclude certain numbers from being incremented:

1. Open the sidebar in the 3D View (press N).
2. Go to the "Tool" tab and find the "Increment Name" panel.
3. Click "Add Pattern" and enter the text pattern you want to exclude from incrementing.

For example, if you have objects named "1WALLN" and want to increment the "N" instead of the "1", add "1WALL" as an escape pattern.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please read the CONTRIBUTING.md file for guidelines.
