import pygame as pg
import builtins
from main import main_loop

def test_main_quit(monkeypatch):
    # Емуляція натискання кнопки закриття гри
    pg.init()
    pg.display.set_mode((640, 640))

    monkeypatch.setattr(pg.event, "get", lambda: [pg.event.Event(pg.QUIT)])
    monkeypatch.setattr(builtins, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code)))

    try:
        main_loop()
    except SystemExit as e:
        assert e.code == 0
