#!/usr/bin/env python3

import math
import argparse

parser = argparse.ArgumentParser(description='Find a terrain following path.')
parser.add_argument('-r', '--resolution', metavar='GRID_RESOLUTION',
                    type=int, default=100,
                    help='grid resolution in meters (default 100)')
parser.add_argument('grid', metavar="GRID_FILE",
                    help='grid file')
args = parser.parse_args()

# bounds for Austria in WGS84 / Pseudo-Mercator (EPSG 3857)
grid_orig = (1060000., 6280000.) # upper left corner
grid_end  = (1910000., 5840000.) # lower right corner

# distortion scaling factor at a reference latitude of 47.5 deg
distortion = 1. / math.cos(47.5 * math.pi / 180.)
grid_scale = distortion * args.resolution

###############################################################################
# initialize grid

from geogrid import GeoGrid

print(f"Loading grid ...")

grid = GeoGrid.load(
    args.grid, grid_scale, grid_orig
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
#coord_start = (1373668.944570, 6052995.719446)
#coord_goal  = (1526447.454855, 5873019.959034)
coord_start = (1615267.281722, 6207771.147095)
coord_goal  = (1862674.833024, 6223846.809606)

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
# generate output map

from geodraw import GeoDraw

print("Generating output image ...")
draw = GeoDraw(grid.size)
draw.fill_palette(
    (coord, val / 4500.) for coord, val in (
        ((x, y), grid.get_node_value((x, y))) for x in range(grid.size[0])
                                              for y in range(grid.size[1])
    ) if 0. <= val <= 4500.
)
#draw.fill_palette(
#    ((100 + x, 100 + y), x / 1000.) for x in range(1000) for y in range(100)
#)
draw.fill_color(path, (255, 0, 0))
draw.fill_color([grid_start, grid_goal], (0, 0, 255))
draw.save(args.grid.rsplit('.', 1)[0] + '_path.png')

#total_delta = 0
#for node1, node2 in zip(path, path[1:]):
#    height1 = img.getpixel((node1[0] * grid_skip, node1[1] * grid_skip))
#    height2 = img.getpixel((node2[0] * grid_skip, node2[1] * grid_skip))
#    diff    = abs(height1 - height2)
#    total_delta += diff
#
#print(f"Total delta: {total_delta}")

###############################################################################
# generate altitude profile

path_len = args.resolution * sum(
    math.sqrt((x1 - x2)**2 + (y1 - y2)**2) for (x1, y1), (x2, y2)
                                           in zip(path, path[1:])
)
delta_alt = 0.
min_slope, max_slope = 0., 0.

svg_scale    = (0.1, 1.)
profile_size = (int(path_len * svg_scale[0]), int(4000. * svg_scale[1]))

with open(args.grid.rsplit('.', 1)[0] + '_profile.png', 'w') as svg:
    svg.write('<svg ')
    svg.write(f"width=\"{profile_size[0]}\" height=\"{profile_size[1]}\" ")
    svg.write(f"viewBox=\"0 0 {profile_size[0]} {profile_size[1]}\" ")
    svg.write('xmlns=\"http://www.w3.org/2000/svg\">\n')

    terrain_line = [(0., grid.get_node_value(path[0]))]
    xpos = 0.
    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        dist  = args.resolution * math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
        alt1  = grid.get_node_value((x1, y1))
        alt2  = grid.get_node_value((x2, y2))
        slope = (alt2 - alt1) / dist
        # stats
        delta_alt += abs(alt1 - alt2)
        min_slope  = min(min_slope, slope)
        max_slope  = max(max_slope, slope)
        # svg output
        stops = [
            (255, 255, 255), ((255, 0, 0) if slope >= 0. else (0, 0, 255))
        ]
        color = tuple(
            int((1. - abs(slope)) * stop1 + abs(slope) * stop2)
            for stop1, stop2 in zip(stops[0], stops[1])
        )
        alt1, alt2 = alt1 * svg_scale[1], alt2 * svg_scale[1]
        svg.write(f"  <polygon points=\"")
        svg.write(f"{xpos                      },{profile_size[1]       } ")
        svg.write(f"{xpos + dist * svg_scale[0]},{profile_size[1]       } ")
        svg.write(f"{xpos + dist * svg_scale[0]},{profile_size[1] - alt2} ")
        svg.write(f"{xpos                      },{profile_size[1] - alt1}" )
        svg.write(f"\" fill=\"rgb{color}\" stroke=\"none\" />\n")
        xpos += dist * svg_scale[0]
        terrain_line.append((xpos, alt2))

    svg.write('  <polyline points=\"')
    svg.write(' '.join(f"{x},{profile_size[1] - y}" for x, y in terrain_line))
    svg.write(f"\" fill=\"none\" stroke=\"black\" />\n")

    svg.write('</svg>')

print(f"  path length:      {path_len / 1000.:.3f} km")
print(f"  steepest climb:   {max_slope * 100.:.2f} %")
print(f"  steepest descent: {min_slope * 100.:.2f} %")

#<svg width="391" height="391" viewBox="-70.5 -70.5 391 391" xmlns="http://www.w3.org/2000/svg">
#<rect fill="#fff" stroke="#000" x="-70" y="-70" width="390" height="390"/>
#<g opacity="0.8">
#<rect x="25" y="25" width="200" height="200" fill="lime" stroke-width="4" stroke="pink" />
#   <circle cx="125" cy="125" r="75" fill="orange" />
#   <polyline points="50,150 50,200 200,200 200,100" stroke="red" stroke-width="4" fill="none" />
#   <line x1="50" y1="50" x2="200" y2="200" stroke="blue" stroke-width="4" />
#</g>
#</svg>
