import pygame as pg
from core.game import Game, GameState
import core.common_resources as cr

def test_save_and_load_game_state(tmp_path):
    pg.init()
    cr.screen = pg.display.set_mode((800, 600))  # потрібен для Game
    save_path = tmp_path / "test_game.json"

    game = Game(ai_active=False)
    game.moves_sequence = ["e2e4", "e7e5"]
    game.save_state()

    new_game = Game(ai_active=False)
    new_game.load_state()

    assert new_game.moves_sequence == ["e2e4", "e7e5"]
