"""PDF error report generation for Go game analysis."""

import os
from typing import List, Dict, Tuple
from datetime import datetime

from katago.analysis import PositionAnalysis
from game.game_tree import GameTree, Stone


def categorize_error(point_loss: float) -> str:
    """Categorize error by point loss.

    Args:
        point_loss: Point loss value

    Returns:
        Category name string
    """
    if point_loss >= 10.0:
        return "Blunder"
    elif point_loss >= 7.0:
        return "Error"
    elif point_loss >= 5.0:
        return "Mistake"
    elif point_loss >= 2.0:
        return "Inaccuracy"
    else:
        return "Minor"


def calculate_player_statistics(
    analysis_results: List[PositionAnalysis],
    game_tree: GameTree
) -> Dict[str, Dict]:
    """Calculate error statistics per player.

    Args:
        analysis_results: List of position analyses
        game_tree: Game tree with move history

    Returns:
        Dictionary with statistics for each player:
        {
            'Black': {
                'blunders': 2,
                'errors': 3,
                'mistakes': 5,
                'inaccuracies': 8,
                'total_errors': 18,
                'total_moves': 75,
                'avg_point_loss': 5.2,
                'error_details': [(move_num, point_loss), ...]
            },
            'White': {...}
        }
    """
    # Initialize stats for both players
    stats = {
        'Black': {
            'blunders': 0,
            'errors': 0,
            'mistakes': 0,
            'inaccuracies': 0,
            'total_errors': 0,
            'total_moves': 0,
            'total_point_loss': 0.0,
            'avg_point_loss': 0.0,
            'error_details': []
        },
        'White': {
            'blunders': 0,
            'errors': 0,
            'mistakes': 0,
            'inaccuracies': 0,
            'total_errors': 0,
            'total_moves': 0,
            'total_point_loss': 0.0,
            'avg_point_loss': 0.0,
            'error_details': []
        }
    }

    # Get main line to map move numbers to players
    main_line = game_tree.get_main_line()

    # Count total moves per player
    for node in main_line:
        if node.move is not None or node.is_pass:
            if node.color == Stone.BLACK:
                stats['Black']['total_moves'] += 1
            elif node.color == Stone.WHITE:
                stats['White']['total_moves'] += 1

    # Process each error
    for analysis in analysis_results:
        if not analysis.is_error:
            continue

        move_num = analysis.move_number
        point_loss = analysis.point_loss

        # Get player from game tree
        if move_num < len(main_line):
            node = main_line[move_num]
            if node.color == Stone.BLACK:
                player = 'Black'
            elif node.color == Stone.WHITE:
                player = 'White'
            else:
                continue  # Skip if no color assigned
        else:
            continue

        # Categorize error
        if point_loss >= 10.0:
            stats[player]['blunders'] += 1
        elif point_loss >= 7.0:
            stats[player]['errors'] += 1
        elif point_loss >= 5.0:
            stats[player]['mistakes'] += 1
        elif point_loss >= 2.0:
            stats[player]['inaccuracies'] += 1

        # Update totals
        stats[player]['total_errors'] += 1
        stats[player]['total_point_loss'] += point_loss
        stats[player]['error_details'].append((move_num, point_loss))

    # Calculate averages (per move, not per error)
    for player in ['Black', 'White']:
        if stats[player]['total_moves'] > 0:
            stats[player]['avg_point_loss'] = (
                stats[player]['total_point_loss'] / stats[player]['total_moves']
            )

    return stats


def generate_error_report_pdf(
    analysis_results: List[PositionAnalysis],
    game_tree: GameTree,
    sgf_path: str,
    output_path: str
) -> bool:
    """Generate PDF error report.

    Args:
        analysis_results: List of position analyses
        game_tree: Game tree with move history
        sgf_path: Path to SGF file
        output_path: Path where PDF should be saved

    Returns:
        True if successful, False otherwise
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib import colors
    except ImportError:
        print("ERROR: reportlab not installed. Run: pip install reportlab")
        return False

    try:
        # Calculate statistics
        stats = calculate_player_statistics(analysis_results, game_tree)

        # Get SGF metadata
        sgf_name = os.path.basename(sgf_path)
        board_size = game_tree.board_size
        komi = game_tree.get_komi()
        total_moves = sum(1 for node in game_tree.get_main_line()
                         if node.move is not None or node.is_pass)

        # Create PDF
        pdf = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter

        # Current Y position
        y_pos = height - 1 * inch

        # Title
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(1*inch, y_pos, "Go Game Error Analysis Report")
        y_pos -= 0.4 * inch

        # Game info
        pdf.setFont("Helvetica", 12)
        pdf.drawString(1*inch, y_pos, f"Game: {sgf_name}")
        y_pos -= 0.25 * inch

        pdf.drawString(1*inch, y_pos, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        y_pos -= 0.25 * inch

        pdf.drawString(1*inch, y_pos, f"Board Size: {board_size}x{board_size}, Komi: {komi}")
        y_pos -= 0.25 * inch

        pdf.drawString(1*inch, y_pos, f"Total Moves: {total_moves}")
        y_pos -= 0.5 * inch

        # Player Statistics Header
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(1*inch, y_pos, "Player Statistics:")
        y_pos -= 0.4 * inch

        # BLACK statistics
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(1*inch, y_pos, "BLACK:")
        y_pos -= 0.3 * inch

        pdf.setFont("Helvetica", 11)
        black_stats = stats['Black']
        pdf.drawString(1.2*inch, y_pos, f"Blunders (>=10pts):     {black_stats['blunders']}")
        y_pos -= 0.2 * inch
        pdf.drawString(1.2*inch, y_pos, f"Errors (7-10pts):       {black_stats['errors']}")
        y_pos -= 0.2 * inch
        pdf.drawString(1.2*inch, y_pos, f"Mistakes (5-7pts):      {black_stats['mistakes']}")
        y_pos -= 0.2 * inch
        pdf.drawString(1.2*inch, y_pos, f"Inaccuracies (2-5pts):  {black_stats['inaccuracies']}")
        y_pos -= 0.25 * inch

        # Separator line
        pdf.line(1.2*inch, y_pos, 4*inch, y_pos)
        y_pos -= 0.25 * inch

        pdf.drawString(1.2*inch, y_pos, f"Total Errors:              {black_stats['total_errors']}")
        y_pos -= 0.2 * inch
        pdf.drawString(1.2*inch, y_pos, f"Total Moves:               {black_stats['total_moves']}")
        y_pos -= 0.2 * inch
        pdf.drawString(1.2*inch, y_pos, f"Avg Point Loss per Move:   {black_stats['avg_point_loss']:.2f} pts")
        y_pos -= 0.5 * inch

        # WHITE statistics
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(1*inch, y_pos, "WHITE:")
        y_pos -= 0.3 * inch

        pdf.setFont("Helvetica", 11)
        white_stats = stats['White']
        pdf.drawString(1.2*inch, y_pos, f"Blunders (>=10pts):     {white_stats['blunders']}")
        y_pos -= 0.2 * inch
        pdf.drawString(1.2*inch, y_pos, f"Errors (7-10pts):       {white_stats['errors']}")
        y_pos -= 0.2 * inch
        pdf.drawString(1.2*inch, y_pos, f"Mistakes (5-7pts):      {white_stats['mistakes']}")
        y_pos -= 0.2 * inch
        pdf.drawString(1.2*inch, y_pos, f"Inaccuracies (2-5pts):  {white_stats['inaccuracies']}")
        y_pos -= 0.25 * inch

        # Separator line
        pdf.line(1.2*inch, y_pos, 4*inch, y_pos)
        y_pos -= 0.25 * inch

        pdf.drawString(1.2*inch, y_pos, f"Total Errors:              {white_stats['total_errors']}")
        y_pos -= 0.2 * inch
        pdf.drawString(1.2*inch, y_pos, f"Total Moves:               {white_stats['total_moves']}")
        y_pos -= 0.2 * inch
        pdf.drawString(1.2*inch, y_pos, f"Avg Point Loss per Move:   {white_stats['avg_point_loss']:.2f} pts")
        y_pos -= 0.5 * inch

        # Bar chart comparison
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(1*inch, y_pos, "Error Count Comparison:")
        y_pos -= 0.35 * inch

        # Calculate bar lengths
        max_errors = max(black_stats['total_errors'], white_stats['total_errors'])
        if max_errors > 0:
            black_bar_length = (black_stats['total_errors'] / max_errors) * 3.5 * inch
            white_bar_length = (white_stats['total_errors'] / max_errors) * 3.5 * inch
        else:
            black_bar_length = 0
            white_bar_length = 0

        # Draw BLACK bar
        pdf.setFillColorRGB(0, 0, 0)  # Black
        if black_bar_length > 0:
            pdf.rect(1.5*inch, y_pos, black_bar_length, 0.2*inch, fill=1)
        pdf.setFillColorRGB(0, 0, 0)  # Reset to black for text
        pdf.drawString(1*inch, y_pos + 0.05*inch, "BLACK:")
        pdf.drawString(1.5*inch + black_bar_length + 0.1*inch, y_pos + 0.05*inch,
                      f"{black_stats['total_errors']}")
        y_pos -= 0.3 * inch

        # Draw WHITE bar
        pdf.setFillColorRGB(0.6, 0.6, 0.6)  # Gray for white
        if white_bar_length > 0:
            pdf.rect(1.5*inch, y_pos, white_bar_length, 0.2*inch, fill=1)
        pdf.setFillColorRGB(0, 0, 0)  # Reset to black for text
        pdf.drawString(1*inch, y_pos + 0.05*inch, "WHITE:")
        pdf.drawString(1.5*inch + white_bar_length + 0.1*inch, y_pos + 0.05*inch,
                      f"{white_stats['total_errors']}")
        y_pos -= 0.5 * inch

        # Error Details Table
        if black_stats['total_errors'] > 0 or white_stats['total_errors'] > 0:
            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawString(1*inch, y_pos, "Error Details:")
            y_pos -= 0.3 * inch

            # Collect all errors
            error_list = []
            for move_num, point_loss in black_stats['error_details']:
                category = categorize_error(point_loss)
                error_list.append([str(move_num), "Black", f"{point_loss:.1f} pts", category])

            for move_num, point_loss in white_stats['error_details']:
                category = categorize_error(point_loss)
                error_list.append([str(move_num), "White", f"{point_loss:.1f} pts", category])

            # Sort by move number
            error_list.sort(key=lambda x: int(x[0]))

            # Create table
            table_data = [["Move", "Player", "Point Loss", "Category"]]
            table_data.extend(error_list)

            table = Table(table_data, colWidths=[0.8*inch, 1*inch, 1.2*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))

            # Calculate table height
            table_height = len(table_data) * 0.25 * inch + 0.5 * inch

            # Check if table fits on current page
            if y_pos - table_height < 1 * inch:
                # Start new page
                pdf.showPage()
                y_pos = height - 1 * inch
                pdf.setFont("Helvetica-Bold", 13)
                pdf.drawString(1*inch, y_pos, "Error Details (continued):")
                y_pos -= 0.3 * inch

            # Draw table
            table.wrapOn(pdf, width, height)
            table.drawOn(pdf, 1*inch, y_pos - table_height + 0.5*inch)

        # Save PDF
        pdf.save()
        return True

    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False
