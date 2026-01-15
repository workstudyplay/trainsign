#!/usr/bin/env python
import time

from samplebase import SampleBase
from worker import DataBuffers, MTAWorker, load_stop_data
from matrix import import_matrix

_, _, graphics = import_matrix()


DARK_RED = graphics.Color(110, 0, 0)
RED = graphics.Color(60, 0, 0)
GRAY = graphics.Color(90,90,90)
BLACK = graphics.Color(0, 0, 0)
WHITE = graphics.Color(95,95,95)
GREEN = graphics.Color(0, 110, 0)
BLUE = graphics.Color(0, 10, 155)
DARK_GREEN = graphics.Color(6, 64, 43)
PURPLE = graphics.Color(200, 0, 200)
BRIGHT_ORANGE = graphics.Color(199,110,0)
ORANGE = graphics.Color(255,140,0)
YELLOW = graphics.Color(155,155,0)
BROWN = graphics.Color(59,29,12)

LINE_TEXT_COLOR = WHITE
WIDTH = 64

def get_direction_text(route):
    return "MANHATTAN"

class RunText(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunText, self).__init__(*args, **kwargs)

    def drawCircle(self, canvas,  x, y, color):
        # Draw circle with lines
        graphics.DrawLine(canvas, x+2, y+0, x+6, y+0, color)
        graphics.DrawLine(canvas, x+1, y+1, x+7, y+1, color)
        graphics.DrawLine(canvas, x+0, y+2, x+8, y+2, color)
        graphics.DrawLine(canvas, x+0, y+3, x+8, y+3, color)
        graphics.DrawLine(canvas, x+0, y+4, x+8, y+4, color)
        graphics.DrawLine(canvas, x+0, y+5, x+8, y+5, color)
        graphics.DrawLine(canvas, x+0, y+6, x+8, y+6, color)
        graphics.DrawLine(canvas, x+1, y+7, x+7, y+7, color)
        graphics.DrawLine(canvas, x+2, y+8, x+6, y+8, color)

    def run(self):
        bg_color = BLACK

        # self.matrix, main_canvas, graphics = load_matrix()
        main_canvas = self.canvas

        font = graphics.Font()
        font.LoadFont("fonts/6x10.bdf")

        iconFont = graphics.Font()
        iconFont.LoadFont("fonts/6x10.bdf")

        stationNameFont = graphics.Font()
        stationNameFont.LoadFont("fonts/5x8.bdf")

        stops = load_stop_data("./stops.txt")
        print("Loaded stops.txt data", len(stops))
        buffers = DataBuffers()

        worker = MTAWorker(
            stops=stops,
            configured_stop_ids=["L14N"],  # or ["G14N","L14N"]
            refresh_s=30.0,
            api_key="friend",
            buffers=buffers,
            name="G",
        )
        worker.start()

        buffers2 = DataBuffers()
        worker2 = MTAWorker(
            stops=stops,
            configured_stop_ids=["G14N"],  # or ["G14N","L14N"]
            refresh_s=30.0,
            api_key="friend",
            buffers=buffers2,
            name="L",
        )
        worker2.start()

        self.drawCircle(main_canvas, 1, 20, ORANGE)
        self.drawCircle(main_canvas, 11, 20, GRAY)
        self.drawCircle(main_canvas, 21, 20, PURPLE)

        y_pos = 10
        graphics.DrawText(main_canvas, stationNameFont, 1, y_pos, WHITE, "MTA TRAINSIGN")

        y_pos += 10
        # graphics.DrawText(main_canvas, iconFont, 30, y_pos, WHITE, "10.5.1.152")

        main_canvas = self.matrix.SwapOnVSync(main_canvas)

        time.sleep(2.0)


        while True:
            _, data = buffers.snapshot()
            print("-" * 24)
            for row in data:
                print(f"{row["route_id"]:<2} {row['text']:<16} {row['status']:<4}")
            print("-" * 24)

            try:
                x_pos = 0
                main_canvas.Fill(bg_color.red, bg_color.green, bg_color.blue)
                row_id = 0

                #graphics.DrawText(main_canvas, stationNameFont, 1, 10, LINE_TEXT_COLOR, "GRAHAM AVE")
                #x_pos = 10
                while row_id < 3:
                    row = data[row_id]
                    route = row["route_id"]
                    txt = row["text"]
                    status = row["status"]

                    self.drawCircle(main_canvas, 0, x_pos + 1, getRouteColor(route))
                    c = graphics.Color(110, 99, 0)
                    graphics.DrawText(main_canvas, iconFont, 2, x_pos + 9, BLACK, route)
                    this_color = LINE_TEXT_COLOR
                    if status.strip() == "0m":
                         this_color = GREEN

                    graphics.DrawText(main_canvas, stationNameFont, 13, x_pos + 9, this_color, txt)
                    graphics.DrawText(main_canvas, font, WIDTH+7, x_pos + 9, this_color, status)
                    row_id += 1
                    x_pos += 10
                main_canvas = self.matrix.SwapOnVSync(main_canvas)

            except Exception as err:
                print(f"Unexpected {err=}, {type(err)=}")
                print("Failure rendering board")
            finally:
                print("Rendered board")

            time.sleep(10.0)

            _, data = buffers2.snapshot()
            print("-" * 24)
            for row in data:
                print(f"{row["route_id"]:<2} {row['text']:<16} {row['status']:<4}")
            print("-" * 24)
            try:
                x_pos = 0
                main_canvas.Fill(bg_color.red, bg_color.green, bg_color.blue)

                #graphics.DrawText(main_canvas, stationNameFont, 1, 10, LINE_TEXT_COLOR, "X                X")
                #graphics.DrawText(main_canvas, stationNameFont, 1, 20, LINE_TEXT_COLOR, "XXXXXXXXXXXXXXXXXX")
                #graphics.DrawText(main_canvas, stationNameFont, 1, 30, LINE_TEXT_COLOR, "X                X")
                #main_canvas = self.matrix.SwapOnVSync(main_canvas)
                row_id = 0
                while row_id < 3:
                    row = data[row_id]
                    route = row["route_id"]
                    txt = row["text"]
                    status = row["status"]

                    self.drawCircle(main_canvas, 0, x_pos + 1, getRouteColor(route))
                    c = graphics.Color(110, 99, 0)
                    graphics.DrawText(main_canvas, iconFont, 2, x_pos + 9, BLACK, route)
                    this_color = LINE_TEXT_COLOR
                    if status.strip() == "0m":
                         this_color = GREEN
                    graphics.DrawText(main_canvas, stationNameFont, 13, x_pos + 9, this_color, txt)
                    graphics.DrawText(main_canvas, font, WIDTH+7, x_pos + 9, this_color, status)
                    row_id += 1
                    x_pos += 10
                main_canvas = self.matrix.SwapOnVSync(main_canvas)
            except:
                print("Failure rendering board")
            finally:
                print("Rendered board")

            time.sleep(10.0)


def getRouteColor(route):
    
    if route=="A" or route=="C" or route=="E":
        return BLUE
    
    if route=="1" or route=="2" or route=="3":
        return DARK_RED
    
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
    
    return GRAY

starttime = time.time()
font = graphics.Font()
font.LoadFont("fonts/tom-thumb.bdf")

textColor = GREEN
circleColor = GRAY
circleNumberColor = BLACK

# Main function
if __name__ == "__main__":
    run_text = RunText()
    if (not run_text.process()):
        run_text.print_help()
