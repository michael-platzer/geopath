
from PIL import Image, ImageDraw

class GeoDraw:
    def __init__(self, size, background=(255, 255, 255), palette=None):
        self.img  = Image.new('RGB', size, color=background)
        self.draw = ImageDraw.Draw(self.img)

        # palette initialization
        self.background = background
        self.palette    = palette if palette is not None else [
            (  0, 102,  43), #(  0, 132,  53),
            ( 51, 204,   0),
            (220, 216, 102), #(244, 240, 113),
            (220, 170,  62), #(244, 189,  69),
            (153, 100,  43),
            (180, 180, 180)  #(255, 255, 255)
        ]
        #self.palette    = palette if palette is not None else [
        #    ( 51, 102,   0),
        #    (129, 195,  31),
        #    (255, 255, 204),
        #    (244, 189,  69),
        #    (102,  51,  12),
        #    (102,  51,   0),
        #    (255, 255, 255)
        #]


    def _palette_color(self, val):
        idx = int(val * len(self.palette))
        if idx < 0 or idx + 1 >= len(self.palette):
            return self.background
        offset = val * len(self.palette) - idx
        return tuple(
            int((1. - offset) * stop1 + offset * stop2)
            for stop1, stop2 in zip(self.palette[idx], self.palette[idx + 1])
        )


    def fill_color(self, coords, color):
        for coord in coords:
            self.img.putpixel((coord[0], coord[1]), color)


    def fill_palette(self, vals):
        for coord, val in vals:
            self.img.putpixel((coord[0], coord[1]), self._palette_color(val))


    def save(self, path):
        self.img.save(path)
