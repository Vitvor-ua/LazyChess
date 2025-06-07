import pygame as pg

from core.game import Game, MenuState
from core.event_holder import EventHolder
from core import common_resources as cr
from analyzer_pygame import run_analyzer

def main_loop():
    pg.init()
    cr.screen = pg.display.set_mode([1000, 720])
    cr.event_holder = EventHolder()

    fps = 60
    while not cr.event_holder.should_quit:
        menu = MenuState()
        result = menu.run()
        if cr.event_holder.should_quit or result is None:
            break
        mode, color, limit = result
        if mode == "analyzer":
            run_analyzer()
            continue
        ai_color = "black" if color == "white" else "white"
        game = Game(
            ai_color=ai_color,
            ai_active=(mode == "bot"),
            timed_play=limit is not None,
            time_limit=limit,
        )
        clock = pg.time.Clock()
        while not cr.event_holder.should_quit and not game.return_to_menu:
            cr.event_holder.get_events()
            game.check_events()
            game.render()
            pg.display.update()
            clock.tick(fps)

    pg.quit()

# Додаємо запуск
if __name__ == "__main__":
    main_loop()
