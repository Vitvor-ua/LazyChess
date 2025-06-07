import json
from core.sprite import Sprite


def contains_text(src:str,text:str):
    return src.find(text) != -1

root = "./assets"
pieces_root = root + "/chess_pieces/"
boards_root = root + "/chess_boards/"

pieces_sprite_dict = {
    'K':Sprite(pieces_root+"white_king.png"),
    'Q':Sprite(pieces_root+"white_queen.png"),
    'R':Sprite(pieces_root+"white_rook.png"),
    'B':Sprite(pieces_root+"white_bishop.png"),
    'N':Sprite(pieces_root+"white_knight.png"),
    'P':Sprite(pieces_root+"white_pawn.png"),

    'k':Sprite(pieces_root+"black_king.png"),
    'q':Sprite(pieces_root+"black_queen.png"),
    'r':Sprite(pieces_root+"black_rook.png"),
    'b':Sprite(pieces_root+"black_bishop.png"),
    'n':Sprite(pieces_root+"black_knight.png"),
    'p':Sprite(pieces_root+"black_pawn.png"),
}

boards_sprite_dict = {
    'classic_board':Sprite(boards_root+"board_empty.png")
}

boards_json_dict = {
    'classic_board': json.loads(open(boards_root + "board_empty.json").read())
}

# Icons for the footer were removed from the repository. Keep the UI dictionary
# empty so the rest of the code can iterate over it without failing.
ui_dict = {}

import os

StockfishPath = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "stockfish",
    "stockfish-windows-x86-64-avx2.exe",
)



