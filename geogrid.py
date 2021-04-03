
import networkx as nx
import math
import shapely.geometry as shp

class GeoGrid:
    def __init__(self, size, scale, orig=(0,0), crs=None, diags=[(1, 1)]):
        assert (len(size) == 2 and isinstance(size[0], int)
                               and isinstance(size[1], int)), (
            "size must be a tuple with two integers")
        assert isinstance(scale, int) or isinstance(scale, float), (
            "scale must be an integer or float")
        self.size  = size
        self.scale = scale
        self.orig  = orig
        self.crs   = crs

        # create the grid
        self.G = nx.grid_2d_graph(size[0], size[1])
        for edge in self.G.edges:
            self.G.edges[edge]['weight'] = self.scale

        # add the diagonals
        for dx, dy in diags:
            diag_wgt = self.scale * math.sqrt(float(dx**2 + dy**2))
            self.G.add_edges_from([
                ((x, y), (x + dx, y + dy)) for x in range(self.size[0] - dx)
                                           for y in range(self.size[1] - dy)
            ] + [
                ((x + dx, y), (x, y + dy)) for x in range(self.size[0] - dx)
                                           for y in range(self.size[1] - dy)
            ], weight=diag_wgt)


    def get_nodes(self):
        return self.G.nodes


    def get_edges(self):
        return self.G.edges


    def rm_nodes(self, nodes):
        for node in nodes:
            try:
                self.G.remove_node(node)
            except nx.NetworkXError:
                pass


    def rm_edges(self, edges):
        for edge in edges:
            try:
                self.G.remove_edge(edge)
            except nx.NetworkXError:
                pass


    def coords_to_grid(self, coords):
        orig_x, orig_y = self.orig
        for x, y in coords:
            yield ((x - orig_x) / self.scale, (orig_y - y) / self.scale)


    def rm_points(self, coords, radius):
        radius /= self.scale
        for cx, cy in self.coords_to_grid(coords):
            self.rm_nodes([
                (x, y) for x in range(int(cx - radius), int(cx + radius + 2.))
                       for y in range(int(cy - radius), int(cy + radius + 2.))
                       if (cx - x)**2 + (cy - y)**2 < radius**2
            ])


    def rm_line(self, coords, margin):
        line = shp.LineString(self.coords_to_grid(coords))
        bounds = (
            int(line.bounds[0]     ), int(line.bounds[1]     ),
            int(line.bounds[2] + 1.), int(line.bounds[3] + 1.)
        )
        margin /= self.scale
        self.rm_nodes([
            (x, y) for x in range(bounds[0], bounds[2] + 1)
                   for y in range(bounds[1], bounds[3] + 1)
                   if line.distance(shp.Point(float(x), float(y))) < margin
        ])


    def rm_polygon(self, coords, offset=None):
        poly = shp.Polygon(self.coords_to_grid(coords))
        if offset is not None:
            poly = poly.buffer(offset / self.scale, resolution=2)
        bounds = (
            int(poly.bounds[0]     ), int(poly.bounds[1]     ),
            int(poly.bounds[2] + 1.), int(poly.bounds[3] + 1.)
        )
        self.rm_nodes([
            (x, y) for x in range(bounds[0], bounds[2] + 1)
                   for y in range(bounds[1], bounds[3] + 1)
                   if poly.contains(shp.Point(float(x), float(y)))
        ])


    def distance(self, node1, node2):
        diff = math.sqrt((node1[0] - node2[0])**2 + (node1[1] - node2[1])**2)
        return diff * self.scale


    def find_path(self, node1, node2):
        heuristic = lambda n1, n2: self.distance(n1, n2)
        return nx.astar_path(self.G, node1, node2, heuristic=heuristic)

