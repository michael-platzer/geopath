
class AirspaceFeature:
    SHAPE_TYPES = {'Point': 1, 'LineString': 2, 'Polygon': 3}

    def __init__(self, json_dict):
        self.feature_id = json_dict['id']
        assert self.feature_id.startswith('airspace.'), "no airspace feature"

        properties = json_dict['properties']
        geometry   = json_dict['geometry']

        self.category  = properties['category']
        self.name      = properties['name']
        self.code      = properties['airspace_code']
        self.reference = properties['external_reference']

        limit_props = ['limit_altitude', 'limit_reference', 'limit_unit']
        lower_limit = [properties[f"lower_{prop}"] for prop in limit_props]
        upper_limit = [properties[f"upper_{prop}"] for prop in limit_props]
        for limit in [lower_limit, upper_limit]:
            if limit[0] != 0 and limit[2] != 'm':
                limit[0] *= {'ft': 0.3048, 'F': 0.3048, 'FL': 30.48}[limit[2]]
        self.lower_limit = tuple(lower_limit[:2])
        self.upper_limit = tuple(upper_limit[:2])

        shape_type = self.SHAPE_TYPES.get(geometry['type'], None)
        assert shape_type is not None, f"unknown primitive {geometry['type']}"

        self.shapes = []
        for line in geometry['coordinates']:
            coords = []
            for coord in line:
                coords.append(tuple(coord))
            self.shapes.append((shape_type, coords))


    def get_shapes(self, altitude=None):
        lower_limit, upper_limit = self.lower_limit[0], self.upper_limit[0]
        if altitude is None or lower_limit <= altitude <= upper_limit:
            for shape in self.shapes:
                yield shape



class GeoJSON:
    def __init__(self, json_dict):
        crs_str  = json_dict['crs']['properties']['name']
        self.crs = int(crs_str[crs_str.index('EPSG::') + 6:])

        self.features = []
        for feature in json_dict['features']:
            feature_id = feature['id']
            if feature_id.startswith('airspace.'):
                self.features.append(AirspaceFeature(feature))
            else:
                raise ValueError(f"unsupported feature with id {feature_id}")


    def get_shapes(self, param=None):
        for feature in self.features:
            for shape in feature.get_shapes(param):
                yield shape
