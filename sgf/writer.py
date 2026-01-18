"""SGF (Smart Game Format) file writer."""

from typing import Tuple
from game.game_tree import GameTree, GameNode
from game.board import Stone


class SGFWriter:
    """Writer for SGF files."""

    @staticmethod
    def write_file(game_tree: GameTree, filename: str) -> None:
        """Write a game tree to an SGF file.

        Args:
            game_tree: GameTree to write
            filename: Output filename
        """
        sgf_content = SGFWriter.tree_to_string(game_tree)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(sgf_content)

    @staticmethod
    def tree_to_string(game_tree: GameTree) -> str:
        """Convert a game tree to SGF string.

        Args:
            game_tree: GameTree to convert

        Returns:
            SGF format string
        """
        sgf = "("
        sgf += SGFWriter._node_to_string(game_tree.root, is_root=True)
        sgf += ")"
        return sgf

    @staticmethod
    def _node_to_string(node: GameNode, is_root: bool = False) -> str:
        """Convert a node and its children to SGF string.

        Args:
            node: GameNode to convert
            is_root: Whether this is the root node

        Returns:
            SGF format string
        """
        sgf = ";"

        # Write properties
        if is_root:
            # Root node properties
            sgf += "FF[4]"  # File format
            sgf += "GM[1]"  # Game type (1 = Go)
            if 'SZ' in node.properties:
                sgf += f"SZ[{node.properties['SZ']}]"
            else:
                sgf += "SZ[19]"

            # Write other root properties
            for key, value in node.properties.items():
                if key not in ('FF', 'GM', 'SZ'):
                    sgf += SGFWriter._property_to_string(key, value)
        else:
            # Move or setup node
            if node.move is not None and not node.is_pass:
                # Regular move
                move_str = SGFWriter._coords_to_sgf(node.move)
                if node.color == Stone.BLACK:
                    sgf += f"B[{move_str}]"
                elif node.color == Stone.WHITE:
                    sgf += f"W[{move_str}]"
            elif node.is_pass:
                # Pass move
                if node.color == Stone.BLACK:
                    sgf += "B[]"
                elif node.color == Stone.WHITE:
                    sgf += "W[]"

            # Write other properties
            for key, value in node.properties.items():
                if key not in ('B', 'W'):
                    sgf += SGFWriter._property_to_string(key, value)

        # Write children
        if node.children:
            # Main line
            if len(node.children) == 1:
                sgf += SGFWriter._node_to_string(node.children[0])
            else:
                # Multiple variations
                for child in node.children:
                    sgf += "("
                    sgf += SGFWriter._node_to_string(child)
                    sgf += ")"

        return sgf

    @staticmethod
    def _property_to_string(key: str, value) -> str:
        """Convert a property to SGF format.

        Args:
            key: Property key
            value: Property value

        Returns:
            SGF format string
        """
        if isinstance(value, list):
            result = ""
            for v in value:
                result += f"{key}[{SGFWriter._escape_value(str(v))}]"
            return result
        else:
            return f"{key}[{SGFWriter._escape_value(str(value))}]"

    @staticmethod
    def _escape_value(value: str) -> str:
        """Escape special characters in property values.

        Args:
            value: Value to escape

        Returns:
            Escaped value
        """
        # Escape backslash and closing bracket
        value = value.replace('\\', '\\\\')
        value = value.replace(']', '\\]')
        return value

    @staticmethod
    def _coords_to_sgf(coords: Tuple[int, int]) -> str:
        """Convert (row, col) to SGF coordinate.

        Args:
            coords: (row, col) tuple

        Returns:
            SGF move string (e.g., 'dd')
        """
        row, col = coords
        return chr(ord('a') + col) + chr(ord('a') + row)
