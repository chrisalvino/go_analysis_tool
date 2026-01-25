"""Analysis export utilities for saving KataGo analysis results."""

from typing import Dict, Any, List, Optional
from katago.analysis import PositionAnalysis, MoveAnalysis
from katago.engine import KataGoEngine
import json
from datetime import datetime


def move_to_gtp(move: Optional[tuple], board_size: int) -> str:
    """Convert (row, col) to GTP format like 'D4'.

    Args:
        move: Tuple of (row, col) or None for pass
        board_size: Size of the board

    Returns:
        GTP format move string
    """
    if move is None:
        return "pass"
    row, col = move
    return KataGoEngine.coords_to_gtp(row, col, board_size)


def serialize_move_analysis(analysis: MoveAnalysis, board_size: int) -> Dict[str, Any]:
    """Convert MoveAnalysis to JSON-serializable dict.

    Args:
        analysis: MoveAnalysis object
        board_size: Size of the board

    Returns:
        Dictionary representation
    """
    return {
        "move": move_to_gtp(analysis.move, board_size) if not analysis.is_pass else "pass",
        "score_lead": round(analysis.score_lead, 2),
        "win_rate": round(analysis.win_rate, 4),
        "visits": analysis.visits,
        "order": analysis.order,
        "pv": analysis.pv[:10]  # Limit PV length to keep file size reasonable
    }


def serialize_position_analysis(analysis: PositionAnalysis, board_size: int) -> Dict[str, Any]:
    """Convert PositionAnalysis to JSON-serializable dict.

    Args:
        analysis: PositionAnalysis object
        board_size: Size of the board

    Returns:
        Dictionary representation
    """
    return {
        "move_number": analysis.move_number,
        "played_move": move_to_gtp(analysis.played_move, board_size),
        "is_error": analysis.is_error,
        "point_loss": round(analysis.point_loss, 2),
        "played_move_analysis": serialize_move_analysis(analysis.played_move_analysis, board_size) if analysis.played_move_analysis else None,
        "top_moves": [serialize_move_analysis(m, board_size) for m in analysis.top_moves]
    }


def export_analysis_to_json(
    analysis_results: List[PositionAnalysis],
    sgf_path: str,
    board_size: int,
    komi: float,
    max_visits: int,
    output_path: str
) -> bool:
    """Export analysis results to JSON file.

    Args:
        analysis_results: List of PositionAnalysis objects
        sgf_path: Path to original SGF file
        board_size: Board size
        komi: Komi value
        max_visits: Max visits used in analysis
        output_path: Path to save JSON file

    Returns:
        True if successful
    """
    import os

    # Count actual moves
    total_moves = sum(1 for a in analysis_results if a.played_move or a.move_number > 0)

    data = {
        "game_info": {
            "sgf_file": os.path.basename(sgf_path),
            "board_size": board_size,
            "komi": komi,
            "total_moves": total_moves,
            "analysis_date": datetime.now().isoformat(),
            "max_visits": max_visits
        },
        "analysis": [
            serialize_position_analysis(a, board_size)
            for a in analysis_results
        ]
    }

    try:
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving analysis: {e}")
        return False


def gtp_to_move(gtp_move: str, board_size: int) -> Optional[tuple]:
    """Convert GTP format like 'D4' to (row, col).

    Args:
        gtp_move: GTP format move string
        board_size: Size of the board

    Returns:
        Tuple of (row, col) or None for pass
    """
    if gtp_move.lower() == "pass":
        return None
    try:
        return KataGoEngine.gtp_to_coords(gtp_move, board_size)
    except:
        return None


def deserialize_move_analysis(data: Dict[str, Any], board_size: int) -> MoveAnalysis:
    """Convert JSON dict to MoveAnalysis object.

    Args:
        data: Dictionary from JSON
        board_size: Size of the board

    Returns:
        MoveAnalysis object
    """
    move_str = data.get("move", "pass")
    is_pass = move_str.lower() == "pass"
    move = None if is_pass else gtp_to_move(move_str, board_size)

    return MoveAnalysis(
        move=move,
        is_pass=is_pass,
        win_rate=data.get("win_rate", 0.5),
        score_lead=data.get("score_lead", 0.0),
        visits=data.get("visits", 0),
        order=data.get("order", 0),
        pv=data.get("pv", [])
    )


def deserialize_position_analysis(data: Dict[str, Any], board_size: int) -> PositionAnalysis:
    """Convert JSON dict to PositionAnalysis object.

    Args:
        data: Dictionary from JSON
        board_size: Size of the board

    Returns:
        PositionAnalysis object
    """
    played_move_str = data.get("played_move", "pass")
    played_move = None if played_move_str.lower() == "pass" else gtp_to_move(played_move_str, board_size)

    # Deserialize played move analysis
    played_move_analysis = None
    if data.get("played_move_analysis"):
        played_move_analysis = deserialize_move_analysis(data["played_move_analysis"], board_size)

    # Deserialize top moves
    top_moves = []
    for move_data in data.get("top_moves", []):
        top_moves.append(deserialize_move_analysis(move_data, board_size))

    return PositionAnalysis(
        move_number=data.get("move_number", 0),
        played_move=played_move,
        played_move_analysis=played_move_analysis,
        top_moves=top_moves,
        is_error=data.get("is_error", False),
        point_loss=data.get("point_loss", 0.0)
    )


def import_analysis_from_json(json_path: str) -> Optional[List[PositionAnalysis]]:
    """Import analysis results from JSON file.

    Args:
        json_path: Path to JSON file

    Returns:
        List of PositionAnalysis objects or None if failed
    """
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        board_size = data.get("game_info", {}).get("board_size", 19)

        results = []
        for analysis_data in data.get("analysis", []):
            results.append(deserialize_position_analysis(analysis_data, board_size))

        return results

    except Exception as e:
        print(f"Error loading analysis from JSON: {e}")
        return None
