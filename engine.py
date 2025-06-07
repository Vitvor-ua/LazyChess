import chess.engine

class ChessEngine:
    def __init__(self, stockfish_path: str):
        self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)

    def analyze(self, board: chess.Board) -> dict:
        info = self.engine.analyse(board, chess.engine.Limit(time=0.1))
        return {
            "score": info["score"].relative.score(mate_score=10000),
            "pv": info.get("pv"),
        }

    def quit(self) -> None:
        self.engine.quit()
