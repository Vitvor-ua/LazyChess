import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import chess
from core.game import GameState
import core.assets as assets
import stockfish


def test_gamestate_round_trip(tmp_path):
    path = tmp_path / "save.json"
    state = GameState(fen=chess.STARTING_FEN, white_clock=1.0, black_clock=2.0, bot=True, moves=["e2e4"])
    state.save(path)
    loaded = GameState.load(path)
    assert state == loaded


def test_bot_move_legality():
    if not os.path.exists(assets.StockfishPath) or not os.access(assets.StockfishPath, os.X_OK):
        return
    engine = stockfish.Stockfish(assets.StockfishPath)
    board = chess.Board()
    engine.set_fen_position(board.fen())
    move = engine.get_best_move()
    assert chess.Move.from_uci(move) in board.legal_moves


