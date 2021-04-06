
from PIL import Image, ImageDraw

class GeoDraw:
    def __init__(self, size, background=(255, 255, 255), palette=None):
        self.img  = Image.new('RGB', size, color=background)
        self.draw = ImageDraw.Draw(self.img)

        # palette initialization
        self.background = background
        self.palette    = palette if palette is not None else [
            (84 , 229, 151),
            (97 , 240, 130),
            (115, 247, 117),
            (148, 254, 133),
            (158, 254, 135),
            (173, 253, 136),
            (180, 254, 139),
            (189, 254, 140),
            (197, 253, 141),
            (207, 254, 144),
            (215, 254, 146),
            (223, 254, 147),
            (231, 254, 149),
            (238, 253, 151),
            (247, 254, 154),
            (254, 254, 155),
            (253, 252, 151),
            (254, 248, 149),
            (253, 242, 146),
            (254, 238, 146),
            (253, 233, 140),
            (254, 225, 135),
            (253, 219, 127),
            (254, 215, 121),
            (253, 206, 125),
            (250, 203, 128),
            (248, 197, 131),
            (246, 197, 134),
            (244, 197, 136),
            (242, 190, 139),
            (240, 188, 143),
            (238, 187, 145),
            (235, 188, 153),
            (235, 194, 164),
            (232, 197, 172),
            (230, 200, 177),
            (223, 198, 179),
            (223, 198, 179),
            (221, 199, 183),
            (224, 207, 194),
            (228, 214, 203),
            (232, 221, 212),
            (235, 226, 219),
            (239, 231, 225),
            (243, 238, 234),
            (246, 240, 236),
            (250, 249, 248),
            (255, 255, 255)
        ]


    def _palette_color(self, val):
        idx = int(val * len(self.palette))
        if idx < 0 or idx >= len(self.palette):
            return self.background
        return self.palette[idx]


    def fill_color(self, coords, color):
        for coord in coords:
            self.img.putpixel(coord, color)


    def fill_palette(self, vals):
        for coord, val in vals:
            self.img.putpixel(coord, self._palette_color(val))


    def save(self, path):
        self.img.save(path)
