#!/usr/bin/env python3

from geotiff import GeoTIFF
from geogrid import GeoGrid

# initialize a grid graph with altitudes from a digital elevation model
def init_topo_grid(grid_size, grid_scale, grid_orig, grid_crs, dem_path):
    grid = GeoGrid(grid_size, grid_scale)
    dem  = GeoTIFF(dem_path)
    # get coordinates of each node w.r.t. grid CSR
    grid_nodes  = grid.get_nodes()
    node_list   = list(grid_nodes)
    node_coords = [
        (grid_orig[0] + x * grid_scale, grid_orig[1] - y * grid_scale)
        for x, y in node_list
    ]
    # convert node coordinates from grid CSR to elevation model raster
    raster_coords = dem.crs_to_raster(grid_crs, node_coords)
    # get the altitude of each node and identify invalid nodes
    invalid_nodes = []
    for node, raster_coord in zip(node_list, raster_coords):
        x, y = raster_coord
        if 0 <= x < dem.img.size[0] and 0<= y <= dem.img.size[1]:
            altitude = dem.img.getpixel(raster_coord)
            if 0. <= altitude <= 5000.:
                grid_nodes[node]['alt'] = altitude
            else:
                invalid_nodes.append(node)
        else:
            invalid_nodes.append(node)
    grid.rm_nodes(invalid_nodes)
    return grid


# grid for Austria in WGS84 / Pseudo-Mercator (EPSG 3857)
grid_csr  = 3857
grid_orig = (1060000., 6280000.) # upper left corner
grid_end  = (1910000., 5840000.) # lower right corner

# desired scale and resulting grid size
grid_scale = 500.
grid_size  = (
    int((grid_end[0] - grid_orig[0]) / grid_scale),
    int((grid_orig[1] - grid_end[1]) / grid_scale)
)
print(grid_size)

# initialize the grid with the digital elevation model
dem_path = 'ogd-10m-at/dhm_at_lamb_10m_2018.tif'
grid     = init_topo_grid(grid_size, grid_scale, grid_orig, grid_csr, dem_path)

print(f"Initialized grid with digital elevation model")


# update edge weights with the additional cost of climbing/descending
slope_factor = 0.001 / (0.05**2)  # accepting 0.1 % longer way to avoid 5 % slope
#slope_factor = 0.01 / (0.05**2)  # accepting 1 % longer way to avoid 5 % slope
#slope_factor = 0.1 / (0.05**2)  # accepting 10 % longer way to avoid 5 % slope
#slope_factor = 0.2 / (0.05**2)  # accepting 20 % longer way to avoid 5 % slope
#slope_factor = 0.4 / (0.05**2)  # accepting 20 % longer way to avoid 5 % slope
#slope_factor = 0.5 / (0.05**2)  # accepting 50 % longer way to avoid 5 % slope
#slope_factor = 1.0 / (0.05**2)  # accepting 100 % longer way to avoid 5 % slope
grid_nodes = grid.get_nodes()
grid_edges = grid.get_edges()
for edge in grid_edges:
    node1, node2 = edge
    diff   = abs(grid_nodes[node1]['alt'] - grid_nodes[node2]['alt'])
    length = grid_edges[edge]['weight']
    slope  = diff / length
    grid_edges[edge]['weight'] = length * (1. + slope_factor * slope**2)

print(f"Updated weight of all edges with slope penalty")


coord_start = (1586302.74, 6202211.87)
coord_goal  = (1783338.24, 5915996.99)

# convert start and goal coordinates to nodes
grid_start = (
    int((coord_start[0] - grid_orig[0]) / grid_scale),
    int((grid_orig[1] - coord_start[1]) / grid_scale)
)
grid_goal = (
    int((coord_goal[0] - grid_orig[0]) / grid_scale),
    int((grid_orig[1] - coord_goal[1]) / grid_scale)
)

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
for node in grid_nodes:
    altitude = grid_nodes[node]['alt']
    out.putpixel(node, terrain_palette[int((altitude / 4000.) * len(terrain_palette))])
for node in path:
    out.putpixel(node, (255, 0, 0))
out.putpixel(grid_start, (0, 0, 255))
out.putpixel(grid_goal , (0, 0, 255))

draw = ImageDraw.Draw(out)
for feature_type, line in tmap.query_shapes(zoom_level, filters):
    line = [
        ((x - grid_orig[0]) / grid_scale, (grid_orig[1] - y) / grid_scale)
        for x, y in line
    ]
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
