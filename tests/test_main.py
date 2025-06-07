import os
import pytest
import chess

def test_import_main():
    try:
        import main
    except Exception as e:
        pytest.fail(f"main.py failed to import: {e}")
