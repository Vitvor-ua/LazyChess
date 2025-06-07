import os
import pygame as pg
import chess
import chess.pgn
import tkinter as tk
from tkinter import filedialog

from engine import ChessEngine
from core.common_functions import expand_fen_row
import core.common_resources as cr


class PygameAnalyzer:
    def __init__(self):
        pg.display.set_caption("Chess Analyzer")
        self.font = pg.font.Font("assets/fonts/english/lazy.ttf", 20)

        self.engine = None
        if os.path.exists(cr.StockfishPath) and os.access(cr.StockfishPath, os.X_OK):
            self.engine = ChessEngine(cr.StockfishPath)

        self.board = chess.Board()
        self.moves: list[chess.Move] = []
        self.move_index = 0
        self.analysis_text = ""
        self.selected_square: chess.Square | None = None
        self.eval_value = 0.0

        # board visuals copied from Game
        self.board_rect = pg.FRect(*cr.boards_json_dict["classic_board"]["board_rect"])
        self.board_sprite = cr.boards_sprite_dict["classic_board"]
        self.resize_board()
        self.create_board_tiles()
        self.resize_pieces()
        self.update_pieces_map()

    def resize_board(self) -> None:
        board_size = cr.screen.get_height()
        self.board_sprite.transform(board_size, board_size)
        m = self.board_sprite.get_diff()[0]
        self.board_rect.x *= m
        self.board_rect.y *= m
        self.board_rect.w *= m
        self.board_rect.h *= m
        self.board_rect.w += 1
        self.board_rect.h += 1

    def create_board_tiles(self) -> None:
        w = self.board_rect.w / 8
        h = self.board_rect.h / 8
        self.board_map = {}
        letters = "abcdefgh"
        digits = "12345678"
        for x, letter in enumerate(letters):
            for y, digit in enumerate(digits[::-1]):
                rect = pg.FRect(x * w, y * h, w, h)
                rect.x += self.board_rect.x
                rect.y += self.board_rect.y
                uci = letter + digit
                self.board_map[uci] = rect

    def resize_pieces(self) -> None:
        tallest = cr.pieces_sprite_dict["r"]
        h = self.board_rect.h / 8
        for name in cr.pieces_sprite_dict:
            sprite = cr.pieces_sprite_dict[name]
            if sprite.raw_surface.get_height() > tallest.raw_surface.get_height():
                tallest = sprite
        tallest.transform_by_height(h)
        rel = tallest.get_diff()
        for name in cr.pieces_sprite_dict:
            sprite = cr.pieces_sprite_dict[name]
            sprite.transform_by_rel(rel[0], rel[1])

    def update_pieces_map(self) -> None:
        fen = self.board.board_fen()
        new_fen = [expand_fen_row(i) for i in fen.split("/")]
        pieces = {}
        for row, digit in zip(new_fen, "87654321"):
            for column, letter in zip(row, "abcdefgh"):
                if column != "0":
                    pieces[letter + digit] = column
        self.pieces_map = pieces
        # The SimpleEngine instance does not maintain state between calls, so
        # there is no need to manually set the engine position here. The board
        # is provided directly to the analyze/play calls.
        # (Using set_position here caused an AttributeError.)

    def load_pgn(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as fh:
            game = chess.pgn.read_game(fh)
        if game:
            self.board = game.board()
            self.moves = list(game.mainline_moves())
            self.move_index = 0
        self.update_pieces_map()
        self.analyze_position()

    def analyze_position(self) -> None:
        if not self.engine:
            self.analysis_text = "Engine not found"
            self.eval_value = 0.0
            return
        info = self.engine.analyze(self.board)
        score = info["score"]
        self.analysis_text = f"Score: {score}"
        if info.get("pv"):
            self.analysis_text += f"  Best: {info['pv'][0]}"
        if isinstance(score, int):
            val = score / 100
        else:
            val = score.relative.score()
        if val > 1:
            val = 1
        elif val < -1:
            val = -1
        self.eval_value = (val + 1) / 2

    def next_move(self) -> None:
        if self.move_index < len(self.moves):
            self.board.push(self.moves[self.move_index])
            self.move_index += 1
            self.update_pieces_map()
            self.analyze_position()

    def prev_move(self) -> None:
        if self.move_index > 0:
            self.move_index -= 1
            self.board.pop()
            self.update_pieces_map()
            self.analyze_position()

    def handle_click(self, pos: tuple[int, int]) -> None:
        for uci, rect in self.board_map.items():
            if rect.collidepoint(pos):
                square = chess.parse_square(uci)
                if self.selected_square is None:
                    if self.board.piece_at(square):
                        self.selected_square = square
                else:
                    move = chess.Move(self.selected_square, square)
                    if move in self.board.legal_moves:
                        self.board.push(move)
                        self.selected_square = None
                        self.update_pieces_map()
                        self.analyze_position()
                    else:
                        self.selected_square = None
                break

    def draw_board(self) -> None:
        cr.screen.blit(self.board_sprite.transformed_surface, (0, 0))
        for uci, piece in self.pieces_map.items():
            rect = self.board_map[uci]
            img = cr.pieces_sprite_dict[piece].transformed_surface
            img_rect = img.get_rect(center=rect.center)
            cr.screen.blit(img, img_rect)
        if self.selected_square is not None:
            name = chess.square_name(self.selected_square)
            if name in self.board_map:
                r = self.board_map[name].copy()
                pg.draw.rect(cr.screen, (200, 200, 100), r, width=3)

    def draw_ui(self) -> None:
        panel_x = self.board_rect.right + 20
        instructions = [
            "Arrows: navigate",
            "L: load",
            "R: reset",
        ]
        y_instr = 10
        for line in instructions:
            text = self.font.render(line, True, (255, 255, 255))
            cr.screen.blit(text, (panel_x, y_instr))
            y_instr += text.get_height() + 5

        # Evaluation bar
        bar_rect = pg.Rect(panel_x, self.board_rect.y + 30, 20, self.board_rect.h)
        white_h = self.eval_value * bar_rect.height
        pg.draw.rect(cr.screen, (255, 255, 255), (bar_rect.x, bar_rect.y, bar_rect.w, white_h))
        pg.draw.rect(cr.screen, (0, 0, 0), (bar_rect.x, bar_rect.y + white_h, bar_rect.w, bar_rect.height - white_h))

        x = bar_rect.right + 10
        y = bar_rect.y
        for line in self.analysis_text.split("\n"):
            surf = self.font.render(line, True, (255, 255, 255))
            cr.screen.blit(surf, (x, y))
            y += surf.get_height() + 5

        moves_text = " ".join(m.uci() for m in list(self.board.move_stack)[-8:])
        if moves_text:
            moves_surf = self.font.render(moves_text, True, (255, 255, 255))
            cr.screen.blit(moves_surf, (x, y))

    def run(self) -> None:
        clock = pg.time.Clock()
        running = True
        while running:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_RIGHT:
                        self.next_move()
                    elif event.key == pg.K_LEFT:
                        self.prev_move()
                    elif event.key == pg.K_r:
                        self.board.reset()
                        self.move_index = 0
                        self.update_pieces_map()
                        self.analyze_position()
                    elif event.key == pg.K_l:
                        tk_root = tk.Tk()
                        tk_root.withdraw()
                        path = filedialog.askopenfilename(filetypes=[("PGN", "*.pgn")])
                        tk_root.destroy()
                        if path:
                            self.load_pgn(path)
                elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
            cr.screen.fill((0, 0, 0))
            self.draw_board()
            self.draw_ui()
            pg.display.flip()
            clock.tick(30)

        if self.engine:
            self.engine.quit()

def run_analyzer() -> None:
    analyzer = PygameAnalyzer()
    analyzer.run()
