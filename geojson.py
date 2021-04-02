
class AirspaceFeature:
    def __init__(self, json_dict):
        self.feature_id = json_dict['id']
        assert self.feature_id.startswith('airspace.'), "no airspace feature"

        properties = json_dict['properties']
        geometry   = json_dict['geometry']

        self.category  = properties['category']
        self.name      = properties['name']
        self.code      = properties['airspace_code']
        self.reference = properties['external_reference']

        limit_props = ['limit_altitude', 'limit_unit', 'limit_reference']
        self.lower_limit = tuple(properties[f"lower_{p}"] for p in limit_props)
        self.upper_limit = tuple(properties[f"upper_{p}"] for p in limit_props)

        shape_type = None
        if geometry['type'] == 'Polygon':
            shape_type = 2

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
