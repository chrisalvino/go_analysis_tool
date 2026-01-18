"""SGF (Smart Game Format) file parser."""

import re
from typing import Dict, List, Optional, Tuple
from game.game_tree import GameTree, GameNode
from game.board import Stone


class SGFParser:
    """Parser for SGF files."""

    def __init__(self):
        """Initialize the parser."""
        pass

    @staticmethod
    def parse_file(filename: str) -> GameTree:
        """Parse an SGF file.

        Args:
            filename: Path to SGF file

        Returns:
            GameTree with parsed data
        """
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        return SGFParser.parse_string(content)

    @staticmethod
    def parse_string(sgf_content: str) -> GameTree:
        """Parse SGF string content.

        Args:
            sgf_content: SGF format string

        Returns:
            GameTree with parsed data
        """
        # Remove comments and extra whitespace
        sgf_content = re.sub(r'\s+', ' ', sgf_content)

        # Find the game tree (between outermost parentheses)
        match = re.search(r'\((.*)\)', sgf_content, re.DOTALL)
        if not match:
            raise ValueError("Invalid SGF format: no game tree found")

        tree_content = match.group(1)

        # Create game tree with default size
        game_tree = GameTree(19)

        # Parse the tree structure
        SGFParser._parse_node_sequence(tree_content, game_tree.root, game_tree)

        # Get board size from root properties
        if 'SZ' in game_tree.root.properties:
            game_tree.board_size = game_tree.root.properties['SZ']

        return game_tree

    @staticmethod
    def _parse_node_sequence(content: str, parent_node: GameNode, game_tree: GameTree) -> None:
        """Parse a sequence of nodes.

        Args:
            content: SGF content string
            parent_node: Parent node to attach to
            game_tree: The game tree being built
        """
        current_node = parent_node
        i = 0

        while i < len(content):
            char = content[i]

            if char == ';':
                # New node
                i += 1
                properties, i = SGFParser._parse_properties(content, i)

                # Create node based on properties
                node = None

                # Check for move properties (B or W)
                if 'B' in properties:
                    move = properties['B']
                    if move:
                        row, col = SGFParser._sgf_to_coords(move)
                        node = GameNode(move=(row, col), color=Stone.BLACK, parent=current_node)
                    else:
                        node = GameNode(color=Stone.BLACK, is_pass=True, parent=current_node)

                elif 'W' in properties:
                    move = properties['W']
                    if move:
                        row, col = SGFParser._sgf_to_coords(move)
                        node = GameNode(move=(row, col), color=Stone.WHITE, parent=current_node)
                    else:
                        node = GameNode(color=Stone.WHITE, is_pass=True, parent=current_node)

                else:
                    # Non-move node (e.g., root with setup)
                    node = GameNode(parent=current_node)

                # Set all properties
                node.properties = properties

                # Add to parent
                current_node.children.append(node)
                current_node = node

            elif char == '(':
                # Start of variation
                i += 1
                # Find matching closing parenthesis
                depth = 1
                variation_start = i
                while i < len(content) and depth > 0:
                    if content[i] == '(':
                        depth += 1
                    elif content[i] == ')':
                        depth -= 1
                    i += 1

                variation_content = content[variation_start:i-1]
                SGFParser._parse_node_sequence(variation_content, current_node.parent, game_tree)

            elif char == ')':
                # End of variation
                break

            else:
                i += 1

    @staticmethod
    def _parse_properties(content: str, start: int) -> Tuple[Dict[str, any], int]:
        """Parse properties from a node.

        Args:
            content: SGF content
            start: Starting index

        Returns:
            (properties dict, new index)
        """
        properties = {}
        i = start

        while i < len(content):
            # Skip whitespace
            while i < len(content) and content[i] in ' \n\r\t':
                i += 1

            if i >= len(content) or content[i] in ';()':
                break

            # Read property identifier
            prop_id = ''
            while i < len(content) and content[i].isupper():
                prop_id += content[i]
                i += 1

            if not prop_id:
                break

            # Read property values
            values = []
            while i < len(content) and content[i] == '[':
                i += 1
                value = ''
                while i < len(content) and content[i] != ']':
                    if content[i] == '\\' and i + 1 < len(content):
                        # Escape sequence
                        i += 1
                        value += content[i]
                    else:
                        value += content[i]
                    i += 1
                i += 1  # Skip closing ]
                values.append(value)

            # Store property
            if prop_id == 'SZ':
                properties[prop_id] = int(values[0]) if values else 19
            elif prop_id in ('B', 'W', 'AB', 'AW', 'AE'):
                properties[prop_id] = values[0] if values else ''
            elif prop_id in ('C', 'PB', 'PW', 'BR', 'WR', 'RE', 'KM', 'DT', 'EV', 'RO', 'RU'):
                properties[prop_id] = values[0] if values else ''
            else:
                properties[prop_id] = values

        return properties, i

    @staticmethod
    def _sgf_to_coords(sgf_move: str) -> Tuple[int, int]:
        """Convert SGF coordinate to (row, col).

        Args:
            sgf_move: SGF move string (e.g., 'dd')

        Returns:
            (row, col) tuple
        """
        if len(sgf_move) != 2:
            raise ValueError(f"Invalid SGF move: {sgf_move}")

        col = ord(sgf_move[0]) - ord('a')
        row = ord(sgf_move[1]) - ord('a')
        return row, col
