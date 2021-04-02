
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

import subprocess
import select
import os

class GeoTIFF:
    # raster types
    RASTER_AREA  = 1 # pixel is area
    RASTER_POINT = 2 # pixel is point

    # CRS types
    CRS_PROJECTED  = 1 # 2D projected
    CRS_GEOGRAPHIC = 2 # geographic 2D
    CRS_GEOCENTRIC = 3 # geocentric cartesian 3D

    def __init__(self, path):
        self.img = Image.open(path)
        assert self.img.format == 'TIFF', f"`{path}' is not a TIFF image"

        self.tie_points = self.img.tag[33922]
        self.pix_scale  = self.img.tag[33550]

        keydir = self.img.tag[34735]
        keydir = zip(keydir[4::4], keydir[5::4], keydir[6::4], keydir[7::4])
        self.geokeys = {entry[0]: tuple(entry[1:]) for entry in keydir}

        # get raster type
        self.raster_type = self._get_geotag(1025) # GTRasterTypeGeoKey
        assert self.raster_type in [
            self.RASTER_AREA, self.RASTER_POINT
        ], f"invalid raster type {self.raster_type}"

        # get model CRS
        self.crs_type = self._get_geotag(1024) # GTModelTypeGeoKey
        assert self.crs_type in [
            self.CRS_PROJECTED, self.CRS_GEOGRAPHIC, self.CRS_GEOCENTRIC
        ], f"invalid model type {self.crs_type}"
        if self.crs_type == self.CRS_PROJECTED:
            self.model_crs = self._get_geotag(3072) # ProjectedCRSGeoKey
            if self.model_crs == 32767:
                self.model_crs = self._get_geotag(3074) # ProjectionGeoKey
                if self.model_crs == 32767:
                    # convert GeoTIFF projection method to PROJ method
                    # see https://proj.org/usage/projections.html
                    method = {
                        1 : 'tmerc', # TransverseMercator
                        2 : 'tmerc', # TransvMercator_Modified_Alaska
                        3 : 'omerc', # ObliqueMercator
                        4 : 'omerc', # ObliqueMercator_Laborde
                        5 : 'omerc', # ObliqueMercator_Rosenmund
                        6 : 'omerc', # ObliqueMercator_Spherical
                        7 : 'merc' , # Mercator
                        8 : 'lcc'  , # LambertConfConic_2SP
                        #9 : ''     , # LambertConfConic_Helmert
                        #10: ''     , # LambertAzimEqualArea
                        #11: ''     , # AlbersEqualArea
                        #12: ''     , # AzimuthalEquidistant
                        #13: ''     , # EquidistantConic
                        #14: ''     , # Stereographic
                        #15: ''     , # PolarStereographic
                        #16: ''     , # ObliqueStereographic
                        #17: ''     , # Equirectangular
                        #18: ''     , # CassiniSoldner
                        #19: ''     , # Gnomonic
                        #20: ''     , # MillerCylindrical
                        #21: ''     , # Orthographic
                        #22: ''     , # Polyconic
                        #23: ''     , # Robinson
                        #24: ''     , # Sinusoidal
                        #25: ''     , # VanDerGrinten
                        #26: ''     , # NewZealandMapGrid
                        #27: ''       # TransvMercator_SouthOriented
                    }[self._get_geotag(3075)] # ProjMethodGeoKey
                    # convert GeoTIFF parameters to PROJ parameters
                    # see https://proj.org/usage/projections.html
                    params = {key: self._get_geotag(tag) for tag, key in [
                        (3078, 'lat_1'), # ProjStdParallel1GeoKey
                        (3079, 'lat_2'), # ProjStdParallel2GeoKey
                        (3080, 'lon_0'), # ProjNatOriginLongGeoKey
                        (3081, 'lat_0'), # ProjNatOriginLatGeoKey
                        (3082, 'x_0'  ), # ProjFalseEastingGeoKey
                        (3083, 'y_0'  ), # ProjFalseNorthingGeoKey
                        (3084, 'lon_0'), # ProjFalseOriginLongGeoKey
                        (3085, 'lat_0'), # ProjFalseOriginLatGeoKey
                        (3086, 'x_0'  ), # ProjFalseOriginEastingGeoKey
                        (3087, 'y_0'  ), # ProjFalseOriginNorthingGeoKey
                        (3088, 'lon_0'), # ProjCenterLongGeoKey
                        (3089, 'lat_0'), # ProjCenterLatGeoKey
                        #(3090, ''     ), # ProjCenterEastingGeoKey
                        #(3091, ''     ), # ProjCenterNorthingGeoKey
                        (3092, 'k_0'  ), # ProjScaleAtNatOriginGeoKey
                        (3093, 'k_0'  ), # ProjScaleAtCenterGeoKey
                        #(3094, ''     ), # ProjAzimuthAngleGeoKey
                        #(3095, ''     )  # ProjStraightVertPoleLongGeoKey
                    ] if tag in self.geokeys}
                    # get base CRS and corresponding ellipsoid
                    base = self._get_geotag(2048) # GeodeticCRSGeoKey
                    if base == 4312:
                        params['ellps'] = 'bessel'
                    self.model_crs = (method, base, params)
        else:
            self.model_crs = self._get_geotag(2048) # GeodeticCRSGeoKey


    def _get_geotag(self, key):
        tag, cnt, pos = self.geokeys[key]
        if tag == 0:
            return pos
        if tag == 34736:
            vals = self.img.tag[tag][pos:pos+cnt]
            return vals[0] if len(vals) == 1 else vals
        if tag == 34737:
            return self.img.tag[tag][0][pos:pos+cnt]
        raise ValueError(f"invalid tag {tag}")


    def _cs2cs(self, args, coords):
        command = ' | '.join('cs2cs -f %.12f ' + arg for arg in args)
        proc = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True
        )
        coords     = iter(coords)
        stdin_open = True
        stdout_buf = b''
        while stdin_open or len(stdout_buf) > 0:
            if stdin_open:
                # provide next input
                coord = next(coords, None)
                if coord is not None:
                    txt = ' '.join(str(val) for val in coord) + '\n'
                    proc.stdin.write(txt.encode())
                else:
                    proc.stdin.close()
                    stdin_open = False
                # consume available output without blocking
                rlist, _, _ = select.select([proc.stdout], [], [], 0)
                if len(rlist) > 0:
                    stdout_buf += os.read(proc.stdout.fileno(), 4096)
            # read all remaining output when input is consumed
            if not stdin_open:
                stdout_buf += proc.stdout.read()
            # yield available results
            pos = stdout_buf.find(b'\n')
            if pos >= 0:
                line = stdout_buf[0:pos].decode()
                yield tuple(float(val) for val in line.split())
                stdout_buf = stdout_buf[pos+1:]


    def crs_to_model(self, code, coords):
        model_args = [f"+proj={self.model_crs[0]}"] + [
            f"+{key}={val}" for key, val in self.model_crs[2].items()
        ]
        cs2cs_args = None
        if self.crs_type == self.CRS_PROJECTED:
            # transformation from input CRS to base datum followed by
            # projection from base datum to model
            cs2cs_args = [
                f"+init=epsg:{code} +to +init=epsg:{self.model_crs[1]}",
                f"+init=epsg:{self.model_crs[1]} +to " + ' '.join(model_args)
            ]
        else:
            raise ValueError(f"no conversion for model type {self.crs_type}")
        return self._cs2cs(cs2cs_args, coords)


    def model_to_crs(self, code, coords):
        model_args = [f"+proj={self.model_crs[0]}"] + [
            f"+{key}={val}" for key, val in self.model_crs[2].items()
        ]
        cs2cs_args = None
        if self.crs_type == self.CRS_PROJECTED:
            # inverse projection from model to base datum followed by
            # transformation from base datum to output CRS
            cs2cs_args = [
                ' '.join(model_args) + f" +to +init=epsg:{self.model_crs[1]}",
                f"+init=epsg:{self.model_crs[1]} +to +init=epsg:{code}"
            ]
        else:
            raise ValueError(f"no conversion for model type {self.crs_type}")
        return self._cs2cs(cs2cs_args, coords)


    def model_to_raster(self, coords):
        off = 0.5 if self.raster_type == self.RASTER_POINT else 0.
        for coord in coords:
            yield (
                int((coord[0] - self.tie_points[3]) / self.pix_scale[0] + off),
                int((self.tie_points[4] - coord[1]) / self.pix_scale[1] + off)
            )


    def raster_to_model(self, coords):
        off = 0.5 if self.raster_type == self.RASTER_POINT else 0.
        for coord in coords:
            yield (
                self.tie_points[3] + self.pix_scale[0] * (coord[0] - off),
                self.tie_points[4] - self.pix_scale[1] * (coord[1] - off)
            )


    def crs_to_raster(self, code, coords):
        return self.model_to_raster(self.crs_to_model(code, coords))


    def raster_to_crs(self, code, coords):
        return self.model_to_crs(self.raster_to_model(coords), code)


#dhm = GeoTIFF('ogd-10m-at/dhm_at_lamb_10m_2018.tif')
#print(list(dhm.crs_to_raster(4312, [(16.4951667, 48.2261372)])))
