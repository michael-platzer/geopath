#!/usr/bin/env python3

import math
import argparse
import logging
logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(description='Generate a terrain grid.')
parser.add_argument('-r', '--resolution', metavar='GRID_RESOLUTION',
                    type=int, default=100,
                    help='grid resolution in meters (default 100)')
parser.add_argument('grid', metavar="GRID_FILE.npy",
                    help='grid file')
args = parser.parse_args()

assert args.grid.rsplit('.', 1)[1] == 'npy', (
    "grid file must use file extension *.npy"
)

BASEMAP_LEVEL     = 11
BASEMAP_LINEWIDTH = 300 # width of basemap line features (e.g., highways)
BASEMAP_MARGIN    = 120 # margin around basemap areas (e.g., buildings)
AIRSPACE_MARGIN   = 0   # margin around restricted airspace
UASZONE_MARGIN    = 0   # margin around restricted UAS zones

# bounds for Austria in WGS84 / Pseudo-Mercator (EPSG 3857)
grid_orig = (1060000., 6280000.) # upper left corner
grid_end  = (1910000., 5840000.) # lower right corner

# distortion scaling factor at a reference latitude of 47.5 deg
distortion = 1. / math.cos(47.5 * math.pi / 180.)

# desired scale and resulting grid size
grid_scale = distortion * args.resolution
grid_size  = (
    int((grid_end[0] - grid_orig[0]) / grid_scale),
    int((grid_orig[1] - grid_end[1]) / grid_scale)
)

###############################################################################
# initialize grid

from geotiff import GeoTIFF
from geogrid import GeoGrid

# initialize a grid graph with altitudes from a digital elevation model
def init_topo_grid(grid_size, grid_scale, grid_orig, grid_crs, dem_path):
    grid = GeoGrid(grid_size, grid_scale, grid_orig)
    dem  = GeoTIFF(dem_path)
    # get coordinates of each node w.r.t. grid CSR
    node_list = [
        (x, y) for x in range(grid.size[0]) for y in range(grid.size[1])
    ]
    node_coords = [
        (grid.orig[0] + x * grid.scale, grid.orig[1] - y * grid.scale)
        for x, y in node_list
    ]
    # convert node coordinates from grid CSR to elevation model raster
    raster_coords = dem.crs_to_raster(grid_crs, node_coords)
    # assign each node its respective altitude
    grid.set_node_values(
        (node, dem.img.getpixel(raster_coord))
        for node, raster_coord in zip(node_list, raster_coords)
        if (0 <= raster_coord[0] < dem.img.size[0] and 0 <= raster_coord[1] < dem.img.size[1])
    )
    return grid

print(f"Initializing grid of size {grid_size} ...")

# initialize the grid with the digital elevation model
dem_path = 'ogd-10m-at/dhm_at_lamb_10m_2018.tif'
grid     = init_topo_grid(grid_size, grid_scale, grid_orig, 3857, dem_path)

print(f"Initialized grid with digital elevation model")


###############################################################################
# airspace features

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from geojson import GeoJSON

print("Querying restriced airspace ...")

# get access token
token_url  = 'https://map.dronespace.at/oauth/token'
token_auth = ('AustroDroneWeb', 'AustroDroneWeb')
token_data = {'grant_type': 'client_credentials'}
req = requests.post(token_url, auth=token_auth, data=token_data)
assert req.status_code == 200, f"token request status {req.status_code}"
token = req.json()['access_token']

def ows_request(url, token, typename, dt_start, dt_end):
    feature_req = ET.Element('GetFeature', {
        'xmlns':              "http://www.opengis.net/wfs",
        'service':            "WFS",
        'version':            "1.1.0",
        'outputFormat':       "application/json",
        'xsi:schemaLocation': "http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd",
        'xmlns:xsi':          "http://www.w3.org/2001/XMLSchema-instance",
        'viewParams':         f"window_start:{dt_start.strftime(time_format)};window_end:{dt_end.strftime(time_format)}"
    })
    ET.SubElement(feature_req, 'Query', {'typeName': typename, 'srsName': "EPSG:3857"})
    feature_req = ET.tostring(feature_req, encoding='utf8')
    req_headers = {
        'Content-Type':  'text/xml;charset=UTF-8',
        'Authorization': f"Bearer {token}"
    }
    req = requests.post(url, headers=req_headers, data=feature_req)
    assert req.status_code == 200, f"feature request status {req.status_code}"
    return req.json()

dt_start = datetime.now(timezone.utc)
dt_end   = datetime(
    dt_start.year, dt_start.month, dt_start.day, tzinfo=timezone.utc
) + timedelta(days=0, seconds=3600*24-1, milliseconds=999)
time_format = '%Y-%m-%dT%H:%M:%S.000Z'

ows_url  = 'https://map.dronespace.at/ows'
airspace = GeoJSON(ows_request(ows_url, token, 'airspace', dt_start, dt_end))
uaszone  = GeoJSON(ows_request(ows_url, token, 'uaszone' , dt_start, dt_end))

#for feature in airspace.features:
#    print(f"{feature.category:26}{feature.lower_limit[0]:6} {feature.upper_limit[0]:7}  {feature.code:8}  {feature.name}")

#for feature in uaszone.features:
#    print(f"{feature.category:26}{feature.lower_limit[0]:6} {feature.upper_limit[0]:7}  {(feature.code if feature.code is not None else ''):8}  {feature.name}")


###############################################################################
# basemap features

import tilemap

print("Initializing basemap vector map ...")

tmap = tilemap.VectorTileMap('https://maps.wien.gv.at/basemapv/bmapv/3857/')
zoom_level = BASEMAP_LEVEL
for layer in tmap.get_style_layers(zoom_level):
    print(f"  layer with zoom {zoom_level}: {layer['id']}")

filters = tmap.get_style_filters([
    r'GRENZEN/.*STAATSGRENZE.*',
    r'STRASSENNETZ/.*Autobahn.*',
    r'NUTZUNG/.*Siedlung.*'
], zoom_level)
for layer in filters:
    print(f"  Using layer: {layer}")


###############################################################################
# remove forbidden areas

print("Removing forbidden areas ...")

print("  Removing highways and populated areas ...")

for feature_type, coords in tmap.query_shapes(zoom_level, filters):
    if feature_type == 2:
        grid.rm_line(coords, distortion * BASEMAP_LINEWIDTH / 2)
    elif feature_type == 3:
        grid.rm_polygon(coords, distortion * BASEMAP_MARGIN)
    else:
        raise ValueError(f"Unexpected basemap feature type {feature_type}")

print("  Removing restricted airspace ...")

for feature_type, coords in airspace.get_shapes(200):
    if feature_type == 3:
        grid.rm_polygon(coords, distortion * AIRSPACE_MARGIN)
    else:
        raise ValueError(f"Unexpected airspace feature type {feature_type}")

print("  Removing restricted UAS zones ...")

for feature_type, coords in uaszone.get_shapes(200):
    if feature_type == 3:
        grid.rm_polygon(coords, distortion * UASZONE_MARGIN)
    else:
        raise ValueError(f"Unexpected UAS zone feature type {feature_type}")


###############################################################################
# save map and generate output image

grid.save(args.grid)

from geodraw import GeoDraw

print("Generating output image ...")
draw = GeoDraw(grid.size)
draw.fill_palette(
    (coord, val / 4500.) for coord, val in (
        ((x, y), grid.get_node_value((x, y))) for x in range(grid.size[0])
                                              for y in range(grid.size[1])
    ) if 0. <= val <= 4500.
)
draw.save(args.grid.rsplit('.', 1)[0] + '.png')
