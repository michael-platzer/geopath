#!/usr/bin/env python3

import math
import argparse

parser = argparse.ArgumentParser(description='Find a terrain following path.')
parser.add_argument('-r', '--resolution', metavar='GRID_RESOLUTION',
                    type=int, default=100,
                    help='grid resolution in meters (default 100)')
parser.add_argument('-s', '--slope_factor', metavar='SLOPE_FACTOR',
                    type=int, default=0.1/(0.05**2),
                    help='slope factor used for slope penalty calculation')
parser.add_argument('-e', '--epsilon', metavar='EPSILON',
                    type=float, default=50.,
                    help='epsilon for the Ramer-Douglas-Peucker algorithm')
parser.add_argument('grid', metavar="GRID_FILE.npy",
                    help='grid file')
parser.add_argument('start', metavar="START", help='start node coordinate')
parser.add_argument('goal' , metavar="GOAL" , help='goal node coordinate' )
args = parser.parse_args()

file_base = args.grid.rsplit('.', 1)[0]

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


###############################################################################
# search path

print("Searching path ...")

#coord_start = (1586302.74, 6202211.87)
#coord_goal  = (1783338.24, 5915996.99)
#coord_start = (1373668.944570, 6052995.719446)
#coord_goal  = (1526447.454855, 5873019.959034)

coord_start = tuple(float(val) for val in args.start.split(','))
coord_goal  = tuple(float(val) for val in args.goal.split(','))

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

slope_factor = args.slope_factor / args.resolution**2

try:
    path = grid.find_path(grid_start, grid_goal, slope_factor)
except Exception as e:
    print(str(e))
    path = []

print(f"found a path with {len(path)} points")


###############################################################################
# simplify path using the Ramer-Douglas-Peucker algorithm

def rdp(path, epsilon):
    # extract the coordinates (including height) of start and end node
    x1, y1, z1 = path[ 0][0], path[ 0][1], grid.get_node_value(path[ 0])
    x2, y2, z2 = path[-1][0], path[-1][1], grid.get_node_value(path[-1])
    # calculate the distance from start to end node
    line_len = math.sqrt((x1 - x2)**2 + (y1 - y2)**2 + (z1 - z2)**2)
    assert line_len > 0.
    # get the height of each intermediate point
    alt = [grid.get_node_value(pt) for pt in path[1:-1]]
    # calculate the distance between all intermediate points and the line from
    # start to end node
    dists = [math.sqrt(
        ((y2 - y1) * (z1 - z) - (y1 - y) * (z2 - z2))**2 +
        ((z2 - z1) * (x1 - x) - (z1 - z) * (x2 - x2))**2 +
        ((x2 - x1) * (y1 - y) - (x1 - x) * (y2 - y2))**2
    ) / line_len for (x, y), z in zip(path[1:-1], alt)]
    # get maximum distance
    maxdist = max(dists)
    maxidx  = dists.index(maxdist)
    if maxdist > epsilon:
        # divide and conquer
        res1 = rdp(path[:maxidx+1], epsilon)
        res2 = rdp(path[ maxidx: ], epsilon)
        return res1[:-1] + res2
    return [path[0], path[-1]]

path = rdp(path, args.epsilon)

print(f"simplified the path to {len(path)} points")


###############################################################################
# write output path to KML file

from geotiff import GeoTIFF

path_epsg3857 = [
    (grid.orig[0] + x * grid.scale, grid.orig[1] - y * grid.scale)
    for x, y in path
]
path_wgs84 = GeoTIFF._cs2cs(['EPSG:3857 EPSG:4326'], path_epsg3857)

with open(file_base + '_path.kml', 'w') as kml:
    kml.write( '<?xml version="1.0" encoding="UTF-8"?>\n')
    kml.write( '<kml xmlns="http://www.opengis.net/kml/2.2">\n')
    kml.write( '  <Document>\n')
    kml.write(f"    <name>Terrain Following Path Planner</name>\n")
    kml.write( '    <Placemark>\n')
    kml.write( '      <name>Flight Path</name>\n')
    kml.write( '      <LineString>\n')
    kml.write( '        <coordinates>\n')
    for (x, y), coord in zip(path, path_wgs84):
        flight_alt = grid.get_node_value((x, y)) + 120
        kml.write(f"          {coord[1]},{coord[0]},{flight_alt}\n")
    kml.write( '        </coordinates>\n')
    kml.write( '      </LineString>\n')
    kml.write( '    </Placemark>\n')
    kml.write( '  </Document>\n')
    kml.write( '</kml>\n')


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
draw.save(file_base + '_path.png')

# overlay SVG file
with open(file_base + '_path.svg', 'w') as svg:
    svg.write('<svg ')
    svg.write(f"width=\"{grid.size[0]}\" height=\"{grid.size[1]}\" ")
    svg.write(f"viewBox=\"0 0 {grid.size[0]} {grid.size[1]}\" ")
    svg.write('xmlns=\"http://www.w3.org/2000/svg\">\n')
    svg.write('  <polyline points=\"')
    svg.write(' '.join(f"{x},{y}" for x, y in path))
    svg.write(f"\" fill=\"none\" stroke=\"black\" />\n")
    svg.write('</svg>')

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

with open(file_base + '_profile.png', 'w') as svg:
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
