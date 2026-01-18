#!/usr/bin/env python3
"""Go Analysis Tool - Main Entry Point."""

import sys
import traceback
from ui.main_window import GoAnalysisTool


def main():
    """Run the Go Analysis Tool application."""
    try:
        app = GoAnalysisTool()
        app.mainloop()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting application: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
