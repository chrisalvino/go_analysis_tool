"""Game tree structure for move navigation and variations."""

from typing import Optional, List, Dict, Any, Tuple
from game.board import Stone


class GameNode:
    """A node in the game tree representing a move or game state."""

    def __init__(
        self,
        move: Optional[Tuple[int, int]] = None,
        color: Optional[Stone] = None,
        is_pass: bool = False,
        parent: Optional['GameNode'] = None
    ):
        """Initialize a game node.

        Args:
            move: (row, col) of the move, or None for root
            color: Stone color of the move
            is_pass: Whether this is a pass move
            parent: Parent node in the tree
        """
        self.move = move
        self.color = color
        self.is_pass = is_pass
        self.parent = parent
        self.children: List[GameNode] = []
        self.properties: Dict[str, Any] = {}

    def add_child(self, node: 'GameNode') -> 'GameNode':
        """Add a child node.

        Args:
            node: Child node to add

        Returns:
            The added child node
        """
        node.parent = self
        self.children.append(node)
        return node

    def is_root(self) -> bool:
        """Check if this is the root node.

        Returns:
            True if this is the root
        """
        return self.parent is None

    def get_main_line(self) -> List['GameNode']:
        """Get the main line from root to this node.

        Returns:
            List of nodes from root to this node
        """
        line = []
        node = self
        while node is not None:
            line.append(node)
            node = node.parent
        return list(reversed(line))

    def get_move_number(self) -> int:
        """Get the move number of this node.

        Returns:
            Move number (0 for root, counts only actual moves)
        """
        # Count only nodes with actual moves (not metadata-only nodes)
        move_count = 0
        node = self

        while node.parent is not None:
            if node.move is not None or node.is_pass:
                move_count += 1
            node = node.parent

        return move_count


class GameTree:
    """Game tree for navigating moves and variations."""

    def __init__(self, board_size: int = 19):
        """Initialize game tree.

        Args:
            board_size: Size of the board
        """
        self.root = GameNode()
        self.root.properties['SZ'] = board_size
        self.current = self.root
        self.board_size = board_size

    def add_move(self, row: int, col: int, color: Stone) -> GameNode:
        """Add a move to the current position.

        Args:
            row: Row index
            col: Column index
            color: Stone color

        Returns:
            The new node
        """
        node = GameNode(move=(row, col), color=color)
        self.current.add_child(node)
        self.current = node
        return node

    def add_pass(self, color: Stone) -> GameNode:
        """Add a pass move.

        Args:
            color: Stone color

        Returns:
            The new node
        """
        node = GameNode(color=color, is_pass=True)
        self.current.add_child(node)
        self.current = node
        return node

    def go_to_next(self, variation: int = 0) -> bool:
        """Go to the next move (follow a variation).

        Args:
            variation: Which variation to follow (0 for main line)

        Returns:
            True if successful
        """
        if variation < len(self.current.children):
            self.current = self.current.children[variation]
            return True
        return False

    def go_to_previous(self) -> bool:
        """Go to the previous move.

        Returns:
            True if successful
        """
        if self.current.parent is not None:
            self.current = self.current.parent
            return True
        return False

    def go_to_root(self) -> None:
        """Go to the root of the tree."""
        self.current = self.root

    def go_to_move_number(self, move_num: int) -> bool:
        """Go to a specific move number.

        Args:
            move_num: Move number to go to (0 = root)

        Returns:
            True if successful
        """
        self.go_to_root()

        # Keep going to next until we reach the target move number
        # This handles cases where there are metadata nodes between root and moves
        while self.get_current_move_number() < move_num:
            if not self.go_to_next():
                return False

        return self.get_current_move_number() == move_num

    def get_current_move_number(self) -> int:
        """Get the current move number.

        Returns:
            Move number
        """
        return self.current.get_move_number()

    def has_next(self) -> bool:
        """Check if there is a next move.

        Returns:
            True if there are children
        """
        return len(self.current.children) > 0

    def has_previous(self) -> bool:
        """Check if there is a previous move.

        Returns:
            True if not at root
        """
        return not self.current.is_root()

    def get_variations(self) -> List[GameNode]:
        """Get all variations from current position.

        Returns:
            List of child nodes
        """
        return self.current.children

    def get_main_line(self) -> List[GameNode]:
        """Get all moves in the main line from root (including root).

        Returns:
            List of nodes in main line, starting with root
        """
        nodes = [self.root]  # Start with root node
        node = self.root
        while node.children:
            node = node.children[0]
            nodes.append(node)
        return nodes

    def set_property(self, key: str, value: Any) -> None:
        """Set a property on the current node.

        Args:
            key: Property key
            value: Property value
        """
        self.current.properties[key] = value

    def get_property(self, key: str, default: Any = None) -> Any:
        """Get a property from the current node.

        Args:
            key: Property key
            default: Default value if not found

        Returns:
            Property value
        """
        return self.current.properties.get(key, default)

    def clear_from_current(self) -> None:
        """Clear all moves after the current position."""
        self.current.children = []

    def get_komi(self) -> float:
        """Get komi from root properties.

        Returns:
            Komi value (default 6.5 if not set)
        """
        komi_str = self.root.properties.get('KM', '6.5')
        try:
            return float(komi_str)
        except (ValueError, TypeError):
            return 6.5

    def get_rules(self) -> str:
        """Get rules from root properties.

        Returns:
            Rules string compatible with KataGo (default 'japanese')
            Maps common SGF rule names to KataGo format:
            - 'Japanese' -> 'japanese'
            - 'Chinese' -> 'chinese'
            - 'AGA' -> 'aga'
            - 'New Zealand' -> 'chinese' (closest equivalent)
            - Default -> 'japanese'
        """
        # Try to get rules from root properties
        rules_str = self.root.properties.get('RU', None)

        # If not in root, check first child (similar to handicap stones)
        if rules_str is None:
            main_line = self.get_main_line()
            if len(main_line) > 1 and main_line[1].properties:
                rules_str = main_line[1].properties.get('RU', 'japanese')
            else:
                rules_str = 'japanese'

        # Normalize to lowercase
        rules_lower = str(rules_str).lower()

        # Map SGF rule names to KataGo format
        if 'japanese' in rules_lower:
            return 'japanese'
        elif 'chinese' in rules_lower:
            return 'chinese'
        elif 'aga' in rules_lower:
            return 'aga'
        elif 'new zealand' in rules_lower or 'nz' in rules_lower:
            return 'chinese'  # New Zealand rules are similar to Chinese
        elif 'korean' in rules_lower:
            return 'chinese'  # Korean rules are similar to Chinese
        elif 'tromp' in rules_lower or 'tromp-taylor' in rules_lower:
            return 'tromp-taylor'
        else:
            # Default to japanese if unknown
            return 'japanese'
