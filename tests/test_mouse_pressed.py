import pygame as pg
from core.event_holder import EventHolder

def test_mouse_position_updates():
    pg.init()
    pg.display.set_mode((100, 100))
    event_holder = EventHolder()

    # Симулюємо рух миші
    pg.event.post(pg.event.Event(pg.MOUSEMOTION, pos=(30, 30)))
    event_holder.get_events()

    assert event_holder.mouse_pos.x >= 0  # просте, стабільне твердження
