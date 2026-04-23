"""Standard handicap stone positions for Go."""

from typing import List, Tuple


def get_handicap_positions(board_size: int, handicap: int) -> List[Tuple[int, int]]:
    """Get standard handicap stone positions for a given board size.

    Args:
        board_size: Board size (9, 13, or 19)
        handicap: Number of handicap stones (0-9)

    Returns:
        List of (row, col) positions for handicap stones.
        Returns empty list for handicap 0 or 1.
    """
    if handicap < 2:
        return []

    if board_size == 19:
        star_points = _get_star_points_19()
    elif board_size == 13:
        star_points = _get_star_points_13()
    elif board_size == 9:
        star_points = _get_star_points_9()
    else:
        return []

    # Clamp handicap to available positions
    handicap = min(handicap, len(star_points))
    return star_points[:handicap]


def positions_to_sgf(positions: List[Tuple[int, int]]) -> List[str]:
    """Convert board positions to SGF coordinate strings.

    Args:
        positions: List of (row, col) positions

    Returns:
        List of SGF coordinate strings (e.g., ['pd', 'dp'])
    """
    result = []
    for row, col in positions:
        sgf_col = chr(ord('a') + col)
        sgf_row = chr(ord('a') + row)
        result.append(sgf_col + sgf_row)
    return result


def _get_star_points_19() -> List[Tuple[int, int]]:
    """Get ordered star points for 19x19 board.

    Order follows standard Go convention:
    2: upper-right, lower-left
    3: + lower-right
    4: + upper-left
    5: + center
    6: + left-center, right-center (remove center)
    7: + center (re-add)
    8: + top-center, bottom-center (remove center)
    9: + center (re-add)

    Returns:
        List of (row, col) positions in placement order for up to 9 stones.
    """
    # Star point coordinates on 19x19 (0-indexed)
    # Corners: (3,15), (15,3), (15,15), (3,3)
    # Sides: (9,3), (9,15), (3,9), (15,9)
    # Center: (9,9)

    ur = (3, 15)   # upper-right
    ll = (15, 3)    # lower-left
    lr = (15, 15)   # lower-right
    ul = (3, 3)     # upper-left
    cl = (9, 3)     # center-left
    cr = (9, 15)    # center-right
    tc = (3, 9)     # top-center
    bc = (15, 9)    # bottom-center
    cc = (9, 9)     # center

    return [ur, ll, lr, ul, cc, cl, cr, tc, bc]


def _get_star_points_13() -> List[Tuple[int, int]]:
    """Get ordered star points for 13x13 board.

    Returns:
        List of (row, col) positions in placement order for up to 9 stones.
    """
    # Star point coordinates on 13x13 (0-indexed, star points at 3 and 9)
    ur = (3, 9)     # upper-right
    ll = (9, 3)     # lower-left
    lr = (9, 9)     # lower-right
    ul = (3, 3)     # upper-left
    cc = (6, 6)     # center
    cl = (6, 3)     # center-left
    cr = (6, 9)     # center-right
    tc = (3, 6)     # top-center
    bc = (9, 6)     # bottom-center

    return [ur, ll, lr, ul, cc, cl, cr, tc, bc]


def _get_star_points_9() -> List[Tuple[int, int]]:
    """Get ordered star points for 9x9 board.

    Returns:
        List of (row, col) positions in placement order for up to 9 stones.
    """
    # Star point coordinates on 9x9 (0-indexed, star points at 2 and 6)
    ur = (2, 6)     # upper-right
    ll = (6, 2)     # lower-left
    lr = (6, 6)     # lower-right
    ul = (2, 2)     # upper-left
    cc = (4, 4)     # center
    cl = (4, 2)     # center-left
    cr = (4, 6)     # center-right
    tc = (2, 4)     # top-center
    bc = (6, 4)     # bottom-center

    return [ur, ll, lr, ul, cc, cl, cr, tc, bc]
