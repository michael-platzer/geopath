
import networkx as nx
import math

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
            self.G.remove_node(node)


    def rm_edges(self, edges):
        for edge in edges:
            self.G.remove_edge(edge)


    #def rm_region(self,


    def distance(self, node1, node2):
        diff = math.sqrt((node1[0] - node2[0])**2 + (node1[1] - node2[1])**2)
        return diff * self.scale


    def find_path(self, node1, node2):
        heuristic = lambda n1, n2: self.distance(n1, n2)
        return nx.astar_path(self.G, node1, node2, heuristic=heuristic)

