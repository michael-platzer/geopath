#!/usr/bin/env python3

from geotiff import GeoTIFF
from geogrid import GeoGrid

dhm = GeoTIFF('ogd-10m-at/dhm_at_lamb_10m_2018.tif')
dhm_size  = dhm.img.size
dhm_scale = dhm.pix_scale[0]

# http://voibos.rechenraum.com/voibos/voibos?name=hoehenservice&Koordinate=16.494422,48.225206&CRS=4326
coord = (16.494422, 48.225206)
print(next(dhm.crs_to_model(4326, [coord])))
trans = next(dhm.crs_to_raster(4326, [coord, (14.25, 48.57), (16.02, 46.84)]))
print(trans)

print(dhm.img.getpixel((int(trans[0]), int(trans[1]))))

grossglockner = (12.69525, 47.074867)
print(dhm.img.getpixel(next(dhm.crs_to_raster(4326, [grossglockner]))))


grid_skip = 50
grid_size = (dhm_size[0] // grid_skip, dhm_size[1] // grid_skip)
grid      = GeoGrid(grid_size, dhm_scale * grid_skip)

print(f"Initialized grid")

# remove all nodes with invalid heights
invalid_nodes = []
for node in grid.get_nodes():
    height = dhm.img.getpixel((node[0] * grid_skip, node[1] * grid_skip))
    if height < 0. or height > 5000.:
        invalid_nodes.append(node)
grid.rm_nodes(invalid_nodes)

print(f"Removed {len(invalid_nodes)} invalid nodes")

# update the weight with the additional cost of climbing/descending
slope_factor = 0.001 / (0.05**2)  # accepting 0.1 % longer way to avoid 5 % slope
#slope_factor = 0.01 / (0.05**2)  # accepting 1 % longer way to avoid 5 % slope
#slope_factor = 0.1 / (0.05**2)  # accepting 10 % longer way to avoid 5 % slope
#slope_factor = 0.2 / (0.05**2)  # accepting 20 % longer way to avoid 5 % slope
#slope_factor = 0.4 / (0.05**2)  # accepting 20 % longer way to avoid 5 % slope
#slope_factor = 0.5 / (0.05**2)  # accepting 50 % longer way to avoid 5 % slope
#slope_factor = 1.0 / (0.05**2)  # accepting 100 % longer way to avoid 5 % slope
for edge in grid.get_edges():
    node1, node2 = edge
    height1 = dhm.img.getpixel((node1[0] * grid_skip, node1[1] * grid_skip))
    height2 = dhm.img.getpixel((node2[0] * grid_skip, node2[1] * grid_skip))
    diff    = abs(height1 - height2)

    length = grid.get_edges()[edge]['weight']
    slope  = diff / length

    grid.get_edges()[edge]['weight'] = length * (1. + slope_factor * slope**2)

print(f"Updated weight of all edges with slope penalty")

coords = list(dhm.crs_to_raster(4326, [(14.25, 48.57), (16.02, 46.84)]))
print(coords)
coord_start = coords[0]
coord_goal  = coords[1]

print(f"raster start: {coord_start}, raster goal: {coord_goal}")

grid_start = (int(coord_start[0] / grid_skip), int(coord_start[1] / grid_skip))
grid_goal  = (int(coord_goal [0] / grid_skip), int(coord_goal [1] / grid_skip))

print(f"grid start: {grid_start}, grid goal: {grid_goal}")

path = grid.find_path(grid_start, grid_goal)



terrain_palette = [
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

from PIL import Image, ImageDraw
import tilemap

tmap = tilemap.VectorTileMap('https://maps.wien.gv.at/basemapv/bmapv/3857/')
zoom_level = 6
for layer in tmap.get_style_layers(zoom_level):
    print(f"layer with zoom {zoom_level}: {layer['id']}")

filters = tmap.get_style_filters([r'.*STAATSGRENZE.*', r'.*Autobahn.*'], 6)
for layer in filters:
    print(f"Using layer: {layer}")

out = Image.new('RGB', grid.size, color='white')
for node in grid.get_nodes():
    height = dhm.img.getpixel((node[0] * grid_skip, node[1] * grid_skip))
    #valp = height / 4096.
    #valn = 1. - valp
    #out.putpixel(node, (int(valn * 0x94 + valp * 0xee), int(valn * 0xfe + valp * 0xbb), int(valn * 0x85 + valp * 0x91)))
    out.putpixel(node, terrain_palette[int((height / 4000.) * len(terrain_palette))])
for node in path:
    out.putpixel(node, (255, 0, 0))
out.putpixel(grid_start, (0, 0, 255))
out.putpixel(grid_goal , (0, 0, 255))

def gen_raster_lines(tmap):


draw = ImageDraw.Draw(out)
for feature_type, line in tmap.query_shapes(zoom_level, filters):
    line = [(x / grid_skip, y / grid_skip) for x, y in dhm.crs_to_raster(tmap.crs, line)]
    if feature_type == 2:
        draw.line(line, fill=(255, 0, 255))
    #elif feature_type == 3:
    #    draw.polygon(line, fill=(235,255,170))
out.save('path.png')

#total_delta = 0
#for node1, node2 in zip(path, path[1:]):
#    height1 = img.getpixel((node1[0] * grid_skip, node1[1] * grid_skip))
#    height2 = img.getpixel((node2[0] * grid_skip, node2[1] * grid_skip))
#    diff    = abs(height1 - height2)
#    total_delta += diff
#
#print(f"Total delta: {total_delta}")
