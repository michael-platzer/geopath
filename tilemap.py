
from urllib.parse import urljoin
import requests
import re
import time

import vector_tile_pb2

class VectorTileMap:
    def __init__(self, index_url, style_url=None):
        # load index
        req = requests.get(index_url)
        assert req.status_code == 200, f"{index_url}: status {req.status_code}"
        self.index = req.json()

        # load style
        if style_url is None:
            style_url  = urljoin(index_url, self.index['defaultStyles'])
            style_url += '/root.json'
        req = requests.get(style_url)
        assert req.status_code == 200, f"{style_url}: status {req.status_code}"
        self.style = req.json()

        # extract information from index
        self.tile_url = urljoin(index_url, self.index['tiles'][0])
        refsys    = self.index['tileInfo']['spatialReference']
        self.crs  = refsys.get('latestWkid', refsys['wkid'])
        orig      = self.index['tileInfo']['origin']
        self.orig = (orig['x'], orig['y'])
        self.lods = []
        for lod in self.index['tileInfo']['lods']:
            #self.lods.append((lod['level'], lod['scale']))
            self.lods.append((lod['level'], lod['resolution'] * 512))


    def get_style_layers(self, zoom_level=None):
        for layer in self.style['layers']:
            zoom_range = layer.get('minzoom', 0), layer.get('maxzoom', 256)
            zoom_match = zoom_level is None or (
                zoom_level >= zoom_range[0] and zoom_level <= zoom_range[1]
            )
            if zoom_match:
                yield layer


    # convert style layers to filters (dictionary for filtering features)
    def get_style_filters(self, style_layer_patterns, zoom_level=None):
        filters = {}
        for layer in self.style['layers']:
            for pattern in style_layer_patterns:
                zoom_range = layer.get('minzoom', 0), layer.get('maxzoom', 256)
                zoom_match = zoom_level is None or (
                    zoom_level >= zoom_range[0] and zoom_level <= zoom_range[1]
                )
                if zoom_match and re.match(pattern, layer['id']):
                    source_layer = layer['source-layer']
                    layer_filter = layer.get('filter', None)
                    if layer_filter is None:
                        filters[source_layer] = None
                    else:
                        layer_filter = set([tuple(layer_filter)])
                        prev_filters = filters.get(source_layer, set())
                        if prev_filters is not None:
                            filters[source_layer] = prev_filters | layer_filter
        return filters


    # binary search to find locations of tiles (avoid trying all urls)
    def _get_tile_coords(self, lod_seq, coords=None):
        if coords is None:
            extent = 2**lod_seq[0][0]
            coords = [(x, y) for x in range(extent) for y in range(extent)]
        next_coords = []
        for x, y in coords:
            req = requests.head(self.tile_url.format(z=lod_seq[0][0], y=y, x=x))
            if req.status_code == 200:
                x, y = x * 2, y * 2
                next_coords += [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)]
        if len(lod_seq) == 1:
            return next_coords
        return self._get_tile_coords(lod_seq[1:], next_coords)


    def _get_tiles(self, lod, bufcnt=10):
        level, scale = self.lods[lod]
        coords       = self._get_tile_coords(self.lods[1:lod])
        tilebuf      = []
        for x, y in coords:
            while True:
                try:
                    req = requests.get(self.tile_url.format(z=level, y=y, x=x))
                except ConnectionError:
                    pass
                else:
                    if req.status_code not in [429, 500, 502, 503, 504]:
                        break
                time.sleep(5)
            if req.status_code == 200:
                tile = vector_tile_pb2.Tile()
                tile.ParseFromString(req.content)
                tilebuf.append((tile, (x, y)))
            if len(tilebuf) > bufcnt:
                for tile in tilebuf:
                    yield tile
                tilebuf = []
        for tile in tilebuf:
            yield tile


    def _query_features(self, lod, filters=None):
        for tile, tile_pos in self._get_tiles(lod):
            for layer in tile.layers:
                if filters is None or layer.name in filters:
                    extent = layer.extent
                    for feature in layer.features:
                        if filters is None or filters[layer.name] is None:
                            yield (feature, extent, tile_pos)
                        else:
                            # get tags for this feature
                            tags = {
                                layer.keys[key]: layer.values[val].sint_value
                                for key, val
                                in zip(feature.tags[::2], feature.tags[1::2])
                            }
                            # evaluate filters
                            for op, val1, val2 in filters[layer.name]:
                                if isinstance(val1, str) and val1 in tags:
                                    val1 = tags[val1]
                                if isinstance(val2, str) and val2 in tags:
                                    val2 = tags[val2]
                                if eval(f"{val1} {op} {val2}"):
                                    yield (feature, extent, tile_pos)
                                    break


    def query_shapes(self, lod, filters=None):
        for feature, extent, tile_pos in self._query_features(lod, filters):
            shape = []
            pos   = (0, 0)
            op    = None
            cnt   = 0
            for geometry in feature.geometry:
                if op is None:
                    op  = geometry & 0x7
                    cnt = (geometry >> 3) * 2
                else:
                    val = (geometry >> 1) ^ (-(geometry & 1))
                    if (cnt & 1) == 0:
                        pos = (pos[0] + val, pos[1])
                    else:
                        pos = (pos[0], pos[1] + val)
                        if op == 1:
                            shape.append([pos])
                        elif op == 2:
                            shape[-1].append(pos)
                        else:
                            raise ValueError("invalid geometry command")
                    cnt -= 1
                if op == 7 or cnt == 0:
                    op = None
            for line in shape:
                # convert to coordinates
                x0, y0 = (
                    self.orig[0] + tile_pos[0] * self.lods[lod][1],
                    self.orig[1] - tile_pos[1] * self.lods[lod][1]
                )
                scale  = self.lods[lod][1] / extent
                line   = [(x0 + x * scale, y0 - y * scale) for x, y in line]
                yield (feature.type, line)
