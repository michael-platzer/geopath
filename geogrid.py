
import numpy as np
import networkx as nx
import math
import shapely.geometry as shp
import heapq

class GeoGrid:
    def __init__(self, size, scale, orig=(0,0)):
        assert (len(size) == 2 and isinstance(size[0], int)
                               and isinstance(size[1], int)), (
            "size must be a tuple with two integers")
        assert isinstance(scale, int) or isinstance(scale, float), (
            "scale must be an integer or float")
        self.size  = size
        self.scale = scale
        self.orig  = orig

        # create array for node values
        self.vals = np.full(size, -1., np.float32)


    @staticmethod
    def load(path, scale, orig=(0,0)):
        vals = np.load(path)
        grid = GeoGrid(vals.shape, scale, orig)
        grid.vals = vals
        return grid


    def save(self, path):
        np.save(path, self.vals)


    def init_graph(self, diags=[(1, 1)], length_scale=None):
        if length_scale is None:
            length_scale = self.scale

        # create the nodes
        self.G = nx.empty_graph(0)
        self.G.add_nodes_from(
            (x, y) for x in range(self.size[0]) for y in range(self.size[1])
            if 0. <= self.vals[x, y] <= 5000.
        )

        # add horizontal and vertical edges
        for dx, dy in [(0, 1), (1, 0)]:
            new_edges = (
                ((x, y), (x + dx, y + dy)) for x in range(self.size[0] - dx)
                                           for y in range(self.size[1] - dy)
            )
            self.G.add_edges_from((
                edge for edge in new_edges
                     if (edge[0] in self.G and edge[1] in self.G)
            ), weight=length_scale)

        # add the diagonals
        for dx, dy in diags:
            diag_wgt = length_scale * math.sqrt(float(dx**2 + dy**2))
            new_edges = (
                ((x, y), (x + dx, y + dy)) for x in range(self.size[0] - dx)
                                           for y in range(self.size[1] - dy)
            )
            self.G.add_edges_from((
                edge for edge in new_edges
                     if (edge[0] in self.G and edge[1] in self.G)
            ), weight=diag_wgt)
            new_edges = (
                ((x + dx, y), (x, y + dy)) for x in range(self.size[0] - dx)
                                           for y in range(self.size[1] - dy)
            )
            self.G.add_edges_from((
                edge for edge in new_edges
                     if (edge[0] in self.G and edge[1] in self.G)
            ), weight=diag_wgt)


    def get_nodes(self):
        return self.G.nodes


    def get_edges(self):
        return self.G.edges


    def rm_nodes(self, nodes):
        for x, y in nodes:
            if 0 <= x < self.size[0] and 0 <= y < self.size[1]:
                self.vals[x, y] = -1.
                if hasattr(self, 'G'):
                    try:
                        self.G.remove_node((x, y))
                    except nx.NetworkXError:
                        pass


    def rm_edges(self, edges):
        for edge in edges:
            try:
                self.G.remove_edge(edge)
            except nx.NetworkXError:
                pass


    def set_node_value(self, node, val):
        self.vals[node[0], node[1]] = val


    def set_node_values(self, vals):
        for (x, y), val in vals:
            self.vals[x, y] = val


    def get_node_value(self, node):
        return float(self.vals[node[0], node[1]])


    def get_node_values(self, nodes):
        for x, y in nodes:
            yield float((x, y), self.vals[x, y])


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
        heuristic = lambda n1, n2: math.sqrt((n1[0] - n2[0])**2 + (n1[1] - n2[1])**2)

        camefrom = {}
        g_scores = {node1: 0.}
        f_scores = []
        heapq.heappush(f_scores, (heuristic(node1, node2), 0., node1))

        sqrt2 = math.sqrt(2.)
        deltas = [
            (0, 1, 1.   ), (1,  0, 1.   ), ( 0, -1, 1.   ), (-1, 0, 1.   ),
            (1, 1, sqrt2), (1, -1, sqrt2), (-1, -1, sqrt2), (-1, 1, sqrt2)
        ]

        slope_factor = 0.1 / (0.05**2)
        slope_factor *= 1 / 200**2  # self.scale**2

        while len(f_scores) > 0:
            current_f, current_g, current = heapq.heappop(f_scores)
            # skip old entries that have already been replaced by a newer entry
            # in f_scores
            if current_g != g_scores[current]:
                continue
            if current == node2:
                break
            current_h = self.vals[current[0], current[1]]
            for dx, dy, dist in deltas:
                neighbor   = (current[0] + dx, current[1] + dy)
                neighbor_h = self.vals[neighbor[0], neighbor[1]]
                # skip neighbors that are invalid
                if not (0. <= neighbor_h <= 5000.):
                    continue
                slope = abs(current_h - neighbor_h) / dist
                new_g = current_g + dist * (1. + slope_factor * slope**2)
                neighbor_g = g_scores.get(neighbor, None)
                if neighbor_g is None or new_g < neighbor_g:
                    camefrom[neighbor] = current
                    g_scores[neighbor] = new_g
                    neighbor_f = new_g + heuristic(neighbor, node2)
                    heapq.heappush(f_scores, (neighbor_f, new_g, neighbor))

        if len(f_scores) == 0:
            return []
        path = [node2]
        current = node2
        while current != node1:
            current = camefrom[current]
            path.insert(0, current)
        return path
