
# https://maps.wien.gv.at/basemapv/bmapv/3857/tile/0/0/0.pbf

import vector_tile_pb2

tile = vector_tile_pb2.Tile()
with open('/home/michael/Downloads/0.pbf', 'rb') as f:
    tile.ParseFromString(f.read())

print(tile)
