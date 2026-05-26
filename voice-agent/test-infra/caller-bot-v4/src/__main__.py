"""
src/__main__.py — Entry point for python -m src.main
"""
import sys
from .main import main

if __name__ == "__main__":
    sys.exit(main() if hasattr(main, '__await__') else 0)
