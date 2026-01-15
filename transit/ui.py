import os
from core.matrix import load_matrix, import_matrix
from transit.worker import DataBuffers, MTAWorker, load_stop_data

matrix, _, graphics = import_matrix()

DARK_RED = graphics.Color(110, 0, 0)
RED = graphics.Color(60, 0, 0)
GRAY = graphics.Color(90,90,90)
BLACK = graphics.Color(0, 0, 0)
WHITE = graphics.Color(95,95,95)
GREEN = graphics.Color(0, 110, 0)
BLUE = graphics.Color(0, 10, 155)
DARK_GREEN = graphics.Color(6, 64, 43)
PURPLE = graphics.Color(200, 0, 200)
DARK_PURPLE = graphics.Color(200, 100, 200)
BRIGHT_ORANGE = graphics.Color(199,110,0)
ORANGE = graphics.Color(255,140,0)
YELLOW = graphics.Color(155,155,0)
BROWN = graphics.Color(59,29,12)


def getRouteColor(route):
    
    if route=="A" or route=="C" or route=="E":
        return BLUE
    
    if route=="1" or route=="2" or route=="3":
        return DARK_RED
    
    if route=="7X":
        return DARK_PURPLE
    
    if route=="7":
        return PURPLE
    
    if route=="B" or route=="D" or route=="F" or route=="M":
        return ORANGE
    
    if route=="N" or route=="Q" or route=="R" or route=="W":
        return YELLOW
    
    if route=="J" or route=="Z":
        return BROWN
    
    if route=="4" or route=="5" or route=="6":
        return DARK_GREEN

    if route=="L":
        return GRAY
    
    print ("Unknown route color for ", route)
    return GRAY

def drawCircle(c,  x, y, color):
    # Draw circle with lines
    graphics.DrawLine(c, x+2, y+0, x+6, y+0, color)
    graphics.DrawLine(c, x+1, y+1, x+7, y+1, color)
    graphics.DrawLine(c, x+0, y+2, x+8, y+2, color)
    graphics.DrawLine(c, x+0, y+3, x+8, y+3, color)
    graphics.DrawLine(c, x+0, y+4, x+8, y+4, color)
    graphics.DrawLine(c, x+0, y+5, x+8, y+5, color)
    graphics.DrawLine(c, x+0, y+6, x+8, y+6, color)
    graphics.DrawLine(c, x+1, y+7, x+7, y+7, color)
    graphics.DrawLine(c, x+2, y+8, x+6, y+8, color)
    
LINE_TEXT_COLOR = WHITE
WIDTH = 64
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "../../assets")

font = graphics.Font()
font.LoadFont(os.path.join(ASSETS_DIR, "fonts/tom-thumb.bdf"))

iconFont = graphics.Font()
iconFont.LoadFont(os.path.join(ASSETS_DIR, "fonts/6x10.bdf"))

_, main_canvas, _ = load_matrix()

def draw_stop(stop):

    bg_color = BLACK
    _, data = stop.buffers.snapshot()
    print(f"{stop.stop_id} {stop.name}")
    print("-" * 24)
    for row in data:
        print(f"{row["route_id"]:<2} {row['text']:<16} {row['status']:<4}")
    print("-" * 24)

    try:
        x_pos = 0
        main_canvas.Fill(bg_color.red, bg_color.green, bg_color.blue)
        row_id = 0

        # graphics.DrawText(main_canvas, iconFont, 1, 10, LINE_TEXT_COLOR, stop.name.upper())
        # x_pos = 10
        while row_id < 3:
            row = data[row_id]
            route = row["route_id"]
            txt = row["text"]
            status = row["status"]

            drawCircle(main_canvas, 0, x_pos + 1, getRouteColor(route))
            c = graphics.Color(110, 99, 0)
            graphics.DrawText(main_canvas, iconFont, 2, x_pos + 9, BLACK, route)
            this_color = LINE_TEXT_COLOR
            if status.strip() == "0m":
                this_color = GREEN

            graphics.DrawText(main_canvas, iconFont, 13, x_pos + 9, this_color, txt)
            graphics.DrawText(main_canvas, iconFont, WIDTH+7, x_pos + 9, this_color, status)
            row_id += 1
            x_pos += 10
        return matrix.SwapOnVSync(matrix, main_canvas)
    except Exception as err:
        print(f"Unexpected {err=}, {type(err)=}")
        print("Failure rendering board")
    finally:
        print("Rendered board")
