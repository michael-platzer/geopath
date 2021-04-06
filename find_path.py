#!/usr/bin/env python3

import math

# configuration constants
GRID_RESOLUTION = 200 # grid resolution in meters

# bounds for Austria in WGS84 / Pseudo-Mercator (EPSG 3857)
grid_orig = (1060000., 6280000.) # upper left corner
grid_end  = (1910000., 5840000.) # lower right corner

# distortion scaling factor at a reference latitude of 47.5 deg
distortion = 1. / math.cos(47.5 * math.pi / 180.)
grid_scale = distortion * GRID_RESOLUTION

###############################################################################
# initialize grid

from geogrid import GeoGrid

print(f"Loading grid ...")

grid = GeoGrid.load(
    f"grid_{GRID_RESOLUTION}x{GRID_RESOLUTION}.npy", grid_scale, grid_orig
)

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

from geodraw import GeoDraw

print("Generating output image ...")
draw = GeoDraw(grid.size)
draw.fill_palette(
    (coord, val / 4000.) for coord, val in (
        ((x, y), grid.get_node_value((x, y))) for x in range(grid.size[0])
                                              for y in range(grid.size[1])
    ) if 0. <= val <= 4000.
)
draw.fill_color(path, (255, 0, 0))
draw.fill_color([grid_start, grid_goal], (0, 0, 255))
draw.save(f"path_{GRID_RESOLUTION}x{GRID_RESOLUTION}.png")

#total_delta = 0
#for node1, node2 in zip(path, path[1:]):
#    height1 = img.getpixel((node1[0] * grid_skip, node1[1] * grid_skip))
#    height2 = img.getpixel((node2[0] * grid_skip, node2[1] * grid_skip))
#    diff    = abs(height1 - height2)
#    total_delta += diff
#
#print(f"Total delta: {total_delta}")
