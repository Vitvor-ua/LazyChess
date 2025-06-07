import os
import json
import time
from dataclasses import dataclass
from typing import Optional

import pygame as pg
from pygame.locals import *
from pygame.rect import FRect
from pygame import Surface
import chess
import chess.pgn
import stockfish
from core.common_functions import *
import core.common_resources as cr


@dataclass
class GameState:
    fen: str
    white_clock: float
    black_clock: float
    bot: bool
    moves: list

    def save(self, path: str = "saved_game.json") -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.__dict__, fh)

    @classmethod
    def load(cls, path: str = "saved_game.json") -> "GameState":
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(**data)


class Game:

    def __init__(self, ai_color: str = "black", timed_play: bool = False, ai_active: bool = False, time_limit: Optional[int] = None):

        self.moves_sequence = []
        self.timed_play = timed_play
        self.ai_color = ai_color
        self.last_move_time = time.time()
        self.white_clock = 0.0
        self.black_clock = 0.0
        self.time_limit = time_limit
        self.game_start_time = time.time()
        self.history_open = False
        self.outcome_message: Optional[str] = None
        if os.path.exists(cr.StockfishPath):
            self.engine = stockfish.Stockfish(cr.StockfishPath)
        else:
            print(f"Engine was not found. {cr.StockfishPath} does not exist.")
            self.engine = None
        self.board = chess.Board()
        self.board_map = {}  # A map that contains every coord and their co-responding rectangle
        self.pieces_map = {}

        self.board_rect = FRect(cr.boards_json_dict['classic_board']['board_rect'])
        self.board_sprite = cr.boards_sprite_dict['classic_board']
        self.resize_board()
        self.create_board_tiles()

        self.resize_pieces()
        self.selected_piece = None
        self.selected_piece_valid_moves = []
        self.checkers_list = []

        self.promotion_choice = None
        self.update_pieces_map()

        self.promotion_panel_open = False
        self.promotion_panel_pieces = 'QRBN'
        self.onhold_promotion = None
        self.hovered_promotion_sections = None
        self.promotion_panel = FRect(0, 0, self.board_rect.w / 2, self.board_rect.h / 8)
        self.promotion_panel.center = cr.screen.get_rect().center
        self.promotion_panel_sections = [FRect(self.promotion_panel), FRect(self.promotion_panel),
            FRect(self.promotion_panel), FRect(self.promotion_panel), ]

        self.adjust_promotion_panel()
        self.ai_is_active = ai_active and self.engine is not None
        self.return_to_menu = False

        self.bottom_panel = FRect(0, 0, cr.screen.get_width(), cr.screen.get_height())
        self.bottom_panel_speed = 3
        self.adjust_bottom_panel()
        self.resize_ui_elements()
        self.footer_buttons = ["save", "load", "history", "menu"]
        self.font = pg.font.Font("assets/fonts/english/lazy.ttf", 20)

        self.highlight_color = [150, 200, 150]
        self.move_color = [150, 150, 200]
        self.take_color = [200, 150, 150]
        self.check_color = [250, 20, 20]


    def adjust_bottom_panel( self ) :
        self.bottom_panel.h = cr.screen.get_height() * 0.05
        self.bottom_panel.y = cr.screen.get_width()


    def adjust_promotion_panel( self ) :
        w = self.board_rect.w / 8
        self.promotion_panel_sections[0].w = w
        self.promotion_panel_sections[1].x += w
        self.promotion_panel_sections[1].w = w
        self.promotion_panel_sections[2].x += w * 2
        self.promotion_panel_sections[2].w = w
        self.promotion_panel_sections[3].x += w * 3
        self.promotion_panel_sections[3].w = w


    def resize_ui_elements( self ) :
        for name in cr.ui_dict :
            sprite = cr.ui_dict[name]
            sprite.transform_by_height(self.bottom_panel.h * 0.8)


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


    def create_board_tiles( self ) :
        w = self.board_rect.w / 8
        h = self.board_rect.h / 8

        letters = 'abcdefgh'
        digits = '12345678'

        for x, letter in zip(range(8), letters) :
            for y, digit in zip(range(8), digits[: :-1]) :
                rect = FRect(x * w, y * h, w, h)
                rect.x += self.board_rect.x
                rect.y += self.board_rect.y
                uci = letter + digit
                self.board_map[uci] = rect


    def update_pieces_map( self ) :
        fen = self.board.board_fen()
        if self.engine is not None:
            self.engine.set_position(self.moves_sequence)
        new_fen = [expand_fen_row(i) for i in fen.split('/')]

        pieces = {}

        for row, digit in zip(new_fen, "87654321") :
            for column, letter in zip(row, "abcdefgh") :
                if column != '0' :
                    pieces[letter + digit] = column

        self.pieces_map = pieces
        self.fill_checkers_list()


    def resize_pieces( self ) :
        tallest_piece = cr.pieces_sprite_dict["r"]

        h = self.board_rect.h / 8

        for name in cr.pieces_sprite_dict :
            sprite = cr.pieces_sprite_dict[name]
            if sprite.raw_surface.get_height() > tallest_piece.raw_surface.get_height() :
                tallest_piece = sprite

        tallest_piece.transform_by_height(h)
        rel = tallest_piece.get_diff()

        for name in cr.pieces_sprite_dict :
            sprite = cr.pieces_sprite_dict[name]
            sprite.transform_by_rel(rel[0], rel[1])


    def check_pieces_moving( self ) :
        if cr.event_holder.mouse_pressed_keys[2] :
            self.selected_piece = None
            self.update_pieces_map()

        if not cr.event_holder.mouse_pressed_keys[0] :
            return

        for uci in self.board_map :
            rect = self.board_map[uci]
            if not cr.event_holder.mouse_rect.colliderect(rect) :
                continue

            if uci in self.pieces_map :
                piece = self.pieces_map[uci]
                if (piece.islower() and self.turn == 'black') or (
                        piece.isupper() and self.turn == 'white') :
                    self.selected_piece = None

            if self.selected_piece is None :
                if uci in self.pieces_map :
                    piece = self.pieces_map[uci]
                    if (piece.islower() and self.turn == 'black') or (
                            piece.isupper() and self.turn == 'white') :
                        self.selected_piece = uci
                        self.fill_selected_piece_valid_moves()
            else :
                if uci != self.selected_piece :
                    move = self.selected_piece + uci
                    if self.is_promotion(move) and self.is_legal(move) :
                        if self.promotion_choice is None :
                            self.promotion_panel_open = True
                            self.onhold_promotion = move
                            self.hovered_promotion_sections = None
                            return

                    if self.move(move) :
                        self.selected_piece = None
                        self.hovered_promotion_sections = None
                        self.update_pieces_map()


    def check_promotion_panel( self ) :
        if cr.event_holder.mouse_pressed_keys[2] :
            self.promotion_panel_open = False
            self.hovered_promotion_sections = None

        click = cr.event_holder.mouse_pressed_keys[0]
        for rect, c in zip(self.promotion_panel_sections,
                range(len(self.promotion_panel_sections))) :
            if cr.event_holder.mouse_rect.colliderect(rect) :
                self.hovered_promotion_sections = c
                if click :
                    self.promotion_choice = self.promotion_panel_pieces[c].lower()
                    if self.move(self.onhold_promotion + self.promotion_choice) :
                        self.selected_piece = None
                        self.selected_piece_valid_moves.clear()
                        self.update_pieces_map()

                    self.promotion_choice = None
                    self.promotion_panel_open = False
                    self.hovered_promotion_sections = False
                    break


    def check_bottom_panel(self) -> bool:

        click = cr.event_holder.mouse_pressed_keys[0]

        for name, rect in zip(self.footer_buttons, self.footer_rects):
            if cr.event_holder.mouse_rect.colliderect(rect):
                if click:
                    if name == "menu":
                        self.return_to_menu = True
                        return True
                    if name == "save":
                        self.save_state()
                    if name == "load":
                        self.load_state()
                    if name == "history":
                        self.history_open = not self.history_open


        if cr.event_holder.mouse_pos.y > self.board_rect.y + self.board_rect.h or cr.event_holder.mouse_rect.colliderect(
            self.bottom_panel) :
            if self.bottom_panel.y > cr.screen.get_height() - self.bottom_panel.h :
                self.bottom_panel.y -= self.bottom_panel_speed

            return True

        if self.bottom_panel.y < cr.screen.get_height() :
            self.bottom_panel.y += self.bottom_panel_speed

        return False


    def check_events(self) -> None:
        if self.outcome_message:
            self.check_outcome_buttons()
            return

        self.check_time_loss()

        if self.promotion_panel_open:
            self.check_promotion_panel()
        else:
            if self.turn == self.ai_color and self.ai_is_active:
                if self.engine is not None and self.ai_make_move():
                    self.update_pieces_map()
            if not self.check_bottom_panel():
                self.check_pieces_moving()


    def render_pieces( self ) :
        for uci in self.pieces_map :
            piece_name = self.pieces_map[uci]
            rect = self.board_map[uci]
            piece_rect = cr.pieces_sprite_dict[piece_name].transformed_surface.get_rect()
            piece_rect.center = rect.center

            cr.screen.blit(cr.pieces_sprite_dict[piece_name].transformed_surface, piece_rect)


    def render_valid_moves( self ) :
        if self.selected_piece is None :
            return

        for uci in self.selected_piece_valid_moves :
            target = uci[2 :]
            rect = self.board_map[target].copy()
            rect.x -= 1
            rect.y -= 1
            rect.w += 2
            rect.h += 2

            if target in self.pieces_map or self.board.is_en_passant(chess.Move.from_uci(uci)) :
                pg.draw.rect(cr.screen, self.take_color, rect)
            else :
                pg.draw.rect(cr.screen, self.move_color, rect, width=int(rect.w // 8))

        rect = self.board_map[self.selected_piece].copy()
        rect.x -= 1
        rect.y -= 1
        rect.w += 2
        rect.h += 2
        pg.draw.rect(cr.screen, self.highlight_color, rect, width=int(rect.w // 8))


    def render_checkers( self ) :
        for uci in self.checkers_list :
            rect = self.board_map[uci].copy()
            rect.x -= 1
            rect.y -= 1
            rect.w += 2
            rect.h += 2

            pg.draw.rect(cr.screen, self.check_color, rect)


    def render_promotion_panel( self ) :
        pg.draw.rect(cr.screen, self.highlight_color, self.promotion_panel)

        if self.hovered_promotion_sections is not None :
            pg.draw.rect(cr.screen, self.take_color,
                self.promotion_panel_sections[self.hovered_promotion_sections])

        for index, name in zip(range(4), self.promotion_panel_pieces) :
            if self.turn == 'black' :
                name = name.lower()

            surface = cr.pieces_sprite_dict[name].transformed_surface
            surface_rect = surface.get_rect()
            rect = self.promotion_panel_sections[index]
            surface_rect.center = rect.center
            cr.screen.blit(surface, surface_rect)


    def render_bottom_panel( self ) :
        pg.draw.rect(cr.screen, [130, 140, 160], self.bottom_panel)

        for name, rect in zip(self.footer_buttons, self.footer_rects):
            pg.draw.rect(cr.screen, [90, 90, 110], rect.inflate(-4, -4))
            text = self.font.render(name.capitalize(), True, (255, 255, 255))
            text_rect = text.get_rect(center=rect.center)
            cr.screen.blit(text, text_rect)

    def render_sidebar(self) -> None:
        # Use white text to ensure visibility on dark backgrounds
        moves = self.font.render(
            f"Moves: {len(self.moves_sequence)}", True, (255, 255, 255)
        )
        if self.timed_play:
            w, b = self.get_current_clocks()
            if self.time_limit is not None:
                w = max(0, self.time_limit - w)
                b = max(0, self.time_limit - b)
            time_text = self.font.render(
                f"W: {int(w)}s  B: {int(b)}s", True, (255, 255, 255)
            )
        else:
            time_text = self.font.render(
                f"Time: {int(time.time() - self.game_start_time)}s", True, (255, 255, 255)
            )
        max_w = max(moves.get_width(), time_text.get_width())
        x = cr.screen.get_width() - max_w - 10
        cr.screen.blit(moves, (x, 20))
        cr.screen.blit(time_text, (x, 40))

    def render_history(self) -> None:
        rect = FRect(
            self.board_rect.centerx - self.board_rect.w / 4,
            self.board_rect.centery - self.board_rect.h / 4,
            self.board_rect.w / 2,
            self.board_rect.h / 2,
        )
        pg.draw.rect(cr.screen, (200, 200, 220), rect)
        moves_text = " ".join(self.moves_sequence)
        # History panel text should also be visible against its dark background
        txt = self.font.render(moves_text, True, (255, 255, 255))
        cr.screen.blit(txt, rect.topleft)

    def render_outcome(self) -> None:
        rect = cr.screen.get_rect().inflate(-100, -100)
        pg.draw.rect(cr.screen, (220, 220, 220), rect)
        txt = self.font.render(self.outcome_message, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=(rect.centerx, rect.centery - 20))
        cr.screen.blit(txt, txt_rect)

        for r, name in self.get_outcome_button_rects():
            pg.draw.rect(cr.screen, (90, 90, 110), r)
            t = self.font.render(name, True, (255, 255, 255))
            tr = t.get_rect(center=r.center)
            cr.screen.blit(t, tr)

    def render( self ) :
        cr.screen.fill((0, 0, 0))
        cr.screen.blit(self.board_sprite.transformed_surface, [0, 0])
        self.render_checkers()
        self.render_valid_moves()
        self.render_pieces()

        if self.promotion_panel_open :
            self.render_promotion_panel()

        self.render_bottom_panel()
        self.render_sidebar()
        if self.history_open:
            self.render_history()
        if self.outcome_message:
            self.render_outcome()


    def undo( self ):
        self.selected_piece = None
        x = 1
        if self.ai_is_active:
            x+=1

        for i in range(x):
            try:
                self.board.pop()
                if len(self.moves_sequence):
                    self.moves_sequence.pop(-1)
                self.update_pieces_map()
            except IndexError:
                ...

    def reset( self ):
        self.selected_piece = None
        self.moves_sequence.clear()
        self.board.reset()
        self.update_pieces_map()

    def trigger_ai( self ):
        self.ai_is_active = not self.ai_is_active
        text = 'activated ai'
        if not self.ai_is_active:
            text = 'de' + text

        print(text)

    def save_state(self) -> None:
        state = GameState(
            fen=self.board.fen(),
            white_clock=self.white_clock,
            black_clock=self.black_clock,
            bot=self.ai_is_active,
            moves=self.moves_sequence,
        )
        state.save()

    def load_state(self) -> None:
        try:
            state = GameState.load()
        except FileNotFoundError:
            return
        self.board = chess.Board(state.fen)
        self.moves_sequence = state.moves
        self.white_clock = state.white_clock
        self.black_clock = state.black_clock
        self.ai_is_active = state.bot
        self.update_pieces_map()


    @property
    def turn( self ) :
        result = 'black'
        if self.board.turn :
            result = 'white'

        return result


    @property
    def footer_rects(self):
        w = self.bottom_panel.w / len(self.footer_buttons)
        rects = []
        for idx in range(len(self.footer_buttons)):
            rects.append(
                FRect(
                    self.bottom_panel.x + idx * w,
                    self.bottom_panel.y,
                    w,
                    self.bottom_panel.h,
                )
            )
        return rects

    def ai_make_move( self ):
        move = self.engine.get_best_move()
        return self.move(move)

    def move( self, uci ) :
        if self.is_legal(uci) :
            now = time.time()
            if self.timed_play:
                diff = now - self.last_move_time
                if self.turn == "white":
                    self.white_clock += diff
                else:
                    self.black_clock += diff
            self.board.push_uci(uci)
            self.moves_sequence.append(uci)
            self.last_move_time = now
            self.check_game_over()
            return True

        return False


    def is_legal( self, uci ) :
        if self.is_promotion(uci) :
            uci += 'q'

        return chess.Move.from_uci(uci) in self.board.legal_moves

    def get_current_clocks(self) -> tuple[float, float]:
        """Return the current white and black times including the ongoing move."""
        white = self.white_clock
        black = self.black_clock
        if self.timed_play:
            diff = time.time() - self.last_move_time
            if self.turn == "white":
                white += diff
            else:
                black += diff
        return white, black


    def fill_selected_piece_valid_moves( self ) :
        self.selected_piece_valid_moves.clear()
        for uci in self.board_map :
            if self.selected_piece == uci :
                continue
            move = self.selected_piece + uci
            if self.is_legal(move) :
                self.selected_piece_valid_moves.append(move)


    def fill_checkers_list( self ) :
        self.checkers_list = self.get_checkers_coordination()


    def find_piece( self, name ) :
        for uci in self.pieces_map :
            piece = self.pieces_map[uci]
            if piece == name :
                return uci


    def get_checkers_coordination( self ) :
        if not self.board.is_check() :
            return []

        checkers = str(self.board.checkers()).split('\n')
        checkers = [[c for c in i if c != ' '] for i in checkers]
        result = []
        for row, digit in zip(checkers, '87654321') :
            for cell, letter in zip(row, 'abcdefgh') :
                if cell == '1' :
                    result.append(letter + digit)

        king = 'K'
        if self.turn == 'black' :
            king = 'k'

        result.append(self.find_piece(king))

        return result


    def is_promotion( self, uci ) :
        # Check if move is a pawn promotion
        piece = self.pieces_map[uci[:2]]
        destination = uci[3 :]

        return (piece == 'P' and destination =='8') or (piece=='p' and destination=='1')

    def check_game_over(self) -> None:
        if self.board.is_game_over():
            result = self.board.result()
            if result == "1-0":
                self.outcome_message = "White wins"
            elif result == "0-1":
                self.outcome_message = "Black wins"
            else:
                self.outcome_message = "Draw"

    def check_time_loss(self) -> None:
        if not self.timed_play or self.time_limit is None:
            return
        w, b = self.get_current_clocks()
        if w >= self.time_limit:
            self.outcome_message = "Black wins on time"
        elif b >= self.time_limit:
            self.outcome_message = "White wins on time"

    def get_outcome_button_rects(self) -> list[tuple[FRect, str]]:
        rect = cr.screen.get_rect().inflate(-100, -100)
        btn_w = rect.w / 3 - 10
        y = rect.bottom - 40
        rects = []
        for idx, name in enumerate(["Close", "Menu", "Save"]):
            r = FRect(rect.x + 5 + idx * (btn_w + 5), y, btn_w, 30)
            rects.append((r, name))
        return rects

    def check_outcome_buttons(self) -> None:
        click = cr.event_holder.mouse_pressed_keys[0]
        for r, name in self.get_outcome_button_rects():
            if r.collidepoint(cr.event_holder.mouse_pos) and click:
                if name == "Close":
                    self.outcome_message = None
                elif name == "Menu":
                    self.return_to_menu = True
                elif name == "Save":
                    self.save_pgn()

    def save_pgn(self, path: str = "saved_game.pgn") -> None:
        game = chess.pgn.Game()
        node = game
        board = chess.Board()
        for move in self.moves_sequence:
            mv = chess.Move.from_uci(move)
            node = node.add_variation(mv)
            board.push(mv)
        result = board.result()
        game.headers["Result"] = result
        with open(path, "w", encoding="utf-8") as fh:
            print(game, file=fh, end="\n")


class MenuState:
    """Simple start menu."""

    def __init__(self):
        self.font = pg.font.Font("assets/fonts/english/lazy.ttf", 30)
        self.options = [
            "Play vs Bot",
            "Play vs Human",
            "Play on time",
            "Analyze Game",
            "Exit",
        ]
        self.color_options = ["White", "Black"]
        self.time_options = [("1m", 60), ("3m", 180), ("10m", 600), ("1h", 3600)]

    def run(self) -> Optional[tuple[str, Optional[str], Optional[int]]]:
        choosing_color = False
        choosing_time = False
        time_limit: Optional[int] = None
        while not cr.event_holder.should_quit:
            cr.event_holder.get_events()
            if cr.event_holder.should_quit:
                return None
            click = cr.event_holder.mouse_pressed_keys[0]
            cr.screen.fill((30, 30, 30))
            rects = []
            if choosing_time:
                items = [t[0] for t in self.time_options]
            elif choosing_color:
                items = self.color_options
            else:
                items = self.options
            for i, text in enumerate(items):
                surf = self.font.render(text, True, (255, 255, 255))
                r = surf.get_rect(
                    center=(cr.screen.get_width() / 2, cr.screen.get_height() / 2 + i * 50)
                )
                rects.append((r, text))
                cr.screen.blit(surf, r)
            pg.display.update()
            if click:
                for r, text in rects:
                    if r.collidepoint(cr.event_holder.mouse_pos):
                        if choosing_time:
                            for label, seconds in self.time_options:
                                if label == text:
                                    time_limit = seconds
                                    return ("human", None, time_limit)
                        elif choosing_color:
                            return ("bot", text.lower(), None)
                        if text == "Exit":
                            cr.event_holder.should_quit = True
                            return None
                        if text == "Play vs Bot":
                            choosing_color = True
                            break
                        if text == "Play vs Human":
                            return ("human", None, None)
                        if text == "Play on time":
                            choosing_time = True
                            break
                        if text == "Analyze Game":
                            return ("analyzer", None, None)
                
        return None
