#!/usr/bin/env python3

import math
from geogrid import GeoGrid

# distortion scaling factor at a reference latitude of 47.5 deg
distortion = 1. / math.cos(47.5 * math.pi / 180.)
grid_scale = distortion * 200.

# bounds for Austria in WGS84 / Pseudo-Mercator (EPSG 3857)
grid_orig = (1060000., 6280000.) # upper left corner
grid_end  = (1910000., 5840000.) # lower right corner

print(f"Loading map ...")

grid = GeoGrid.load('grid.npy', grid_scale, grid_orig)

print(f"Initializing graph ...")

grid.init_graph(length_scale=grid.scale/distortion)
grid_edges = grid.get_edges()

print(f"Updating weight of all edges with slope penalty ...")

# update edge weights with the additional cost of climbing/descending
#slope_factor = 0.001 / (0.05**2)  # accepting 0.1 % longer way to avoid 5 % slope
#slope_factor = 0.01 / (0.05**2)  # accepting 1 % longer way to avoid 5 % slope
#slope_factor = 0.1 / (0.05**2)  # accepting 10 % longer way to avoid 5 % slope
#slope_factor = 0.2 / (0.05**2)  # accepting 20 % longer way to avoid 5 % slope
#slope_factor = 0.4 / (0.05**2)  # accepting 20 % longer way to avoid 5 % slope
slope_factor = 0.5 / (0.05**2)  # accepting 50 % longer way to avoid 5 % slope
#slope_factor = 1.0 / (0.05**2)  # accepting 100 % longer way to avoid 5 % slope
for edge in grid_edges:
    node1, node2 = edge
    diff   = abs(grid.get_node_value(node1) - grid.get_node_value(node2))
    length = grid_edges[edge]['weight']
    slope  = diff / length
    grid_edges[edge]['weight'] = length * (1. + slope_factor * slope**2)


###############################################################################
# search path

print("Searching path ...")

#coord_start = (1586302.74, 6202211.87)
#coord_goal  = (1783338.24, 5915996.99)
coord_start = (1373668.944570, 6052995.719446)
coord_goal  = (1526447.454855, 5873019.959034)

# convert start and goal coordinates to nodes
grid_start = (
    int((coord_start[0] - grid.orig[0]) / grid.scale),
    int((grid.orig[1] - coord_start[1]) / grid.scale)
)
grid_goal = (
    int((coord_goal[0] - grid.orig[0]) / grid.scale),
    int((grid.orig[1] - coord_goal[1]) / grid.scale)
)

print(f"  grid start: {grid_start}, grid goal: {grid_goal}")

path = grid.find_path(grid_start, grid_goal)


###############################################################################
# generate output image

from PIL import Image, ImageDraw

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

print("Generating output image ...")

out = Image.new('RGB', grid.size, color='white')
for node in ((x, y) for x in range(grid.size[0]) for y in range(grid.size[1])):
    altitude = grid.get_node_value(node)
    if 0. <= altitude < 4000.:
        out.putpixel(node, terrain_palette[int((altitude / 4000.) * len(terrain_palette))])
for node in path:
    out.putpixel(node, (255, 0, 0))
out.putpixel(grid_start, (0, 0, 255))
out.putpixel(grid_goal , (0, 0, 255))
#draw = ImageDraw.Draw(out)
#for feature_type, line in tmap.query_shapes(zoom_level, filters):
#    line = [
#        ((x - grid.orig[0]) / grid.scale, (grid.orig[1] - y) / grid.scale)
#        for x, y in line
#    ]
#    if feature_type == 2:
#        draw.line(line, fill=(255, 0, 255))
#    #elif feature_type == 3:
#    #    draw.polygon(line, fill=(235,255,170))
#for feature_type, line in airspace.get_shapes():
#    line = [
#        ((x - grid.orig[0]) / grid.scale, (grid.orig[1] - y) / grid.scale)
#        for x, y in line
#    ]
#    if feature_type == 2:
#        draw.line(line, fill=(0, 255, 255))
out.save('path.png')

#total_delta = 0
#for node1, node2 in zip(path, path[1:]):
#    height1 = img.getpixel((node1[0] * grid_skip, node1[1] * grid_skip))
#    height2 = img.getpixel((node2[0] * grid_skip, node2[1] * grid_skip))
#    diff    = abs(height1 - height2)
#    total_delta += diff
#
#print(f"Total delta: {total_delta}")
