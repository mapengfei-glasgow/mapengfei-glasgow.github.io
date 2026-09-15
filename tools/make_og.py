#!/usr/bin/env python3
"""Generate og-image.png (1200x630) + apple-touch-icon.png (180x180) for the site.

Run:  python3 tools/make_og.py      (needs pycairo; uses DejaVu fonts)
"""
import cairo

BG = (13/255, 15/255, 18/255)      # #0d0f12
FG = (227/255, 230/255, 232/255)   # #e3e6e8
MUTED = (154/255, 161/255, 179/255)
FAINT = (107/255, 114/255, 128/255)
PINK = (255/255, 26/255, 129/255)
VIOLET = (66/255, 66/255, 250/255)
SKY = (128/255, 159/255, 255/255)

SERIF = "DejaVu Serif"
SANS = "DejaVu Sans"


def grad_bar(cr, w, y=0, h=4):
    g = cairo.LinearGradient(0, y, w, y)
    g.add_color_stop_rgb(0, *VIOLET)
    g.add_color_stop_rgb(0.5, *PINK)
    g.add_color_stop_rgb(1, *SKY)
    cr.set_source(g)
    cr.rectangle(0, y, w, h)
    cr.fill()


def centered_text(cr, text, family, size, color, cy, weight=cairo.FONT_WEIGHT_BOLD):
    cr.select_font_face(family, cairo.FONT_SLANT_NORMAL, weight)
    cr.set_font_size(size)
    ext = cr.text_extents(text)
    cr.set_source_rgb(*color)
    cr.move_to((cr.get_target().get_width() - ext.width) / 2 - ext.x_bearing,
               cy - ext.y_bearing)
    cr.show_text(text)
    return ext


def og_image(path):
    w, h = 1200, 630
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(s)
    cr.set_source_rgb(*BG)
    cr.paint()
    grad_bar(cr, w)

    # pink dot, centred, above the title
    cr.set_source_rgb(*PINK)
    cr.arc(w / 2, 170, 13, 0, 2 * 3.141592653589793)
    cr.fill()

    centered_text(cr, "English Listening", SERIF, 104, FG, 355)
    centered_text(cr, "Learn English with podcasts - tap any sentence to play", SANS, 34,
                  MUTED, 470, weight=cairo.FONT_WEIGHT_NORMAL)

    cr.select_font_face(SANS, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(28)
    txt = "mapengfei-glasgow.github.io"
    ext = cr.text_extents(txt)
    cr.set_source_rgb(*FAINT)
    cr.move_to((w - ext.width) / 2 - ext.x_bearing, h - 60)
    cr.show_text(txt)
    s.write_to_png(path)
    print("wrote", path)


def apple_icon(path):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 180, 180)
    cr = cairo.Context(s)
    cr.set_source_rgb(*BG)
    cr.paint()
    # Headphone-ish "EL" monogram: a bold E, centred
    cr.select_font_face(SANS, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(118)
    ext = cr.text_extents("E")
    cr.set_source_rgb(*FG)
    cr.move_to((180 - ext.width) / 2 - ext.x_bearing, 96 - ext.y_bearing)
    cr.show_text("E")
    # pink dot top-right
    cr.set_source_rgb(*PINK)
    cr.arc(152, 28, 13, 0, 2 * 3.141592653589793)
    cr.fill()
    s.write_to_png(path)
    print("wrote", path)


if __name__ == "__main__":
    import pathlib
    base = pathlib.Path(__file__).resolve().parent.parent / "english-site" / "static"
    og_image(str(base / "og-image.png"))
    apple_icon(str(base / "apple-touch-icon.png"))
