import random

import networkx as nx


def hierarchy_pos(G, root=None, dx=0.1, vert_gap=0.1, vert_loc=0, xcenter=0.5, seed=None):
    """
    Heavily modified from Joel's answer at https://stackoverflow.com/a/29597209/2966723.
    Licensed under Creative Commons Attribution-Share Alike

    If the graph is a tree this will return the positions to plot this in a
    hierarchical layout.

    G: the graph (must be a tree)

    root: the root node of current branch
    - if the tree is directed and this is not given,
      the root will be found and used
    - if the tree is directed and this is given, then
      the positions will be just for the descendants of this node.
    - if the tree is undirected and not given,
      then a random choice will be used.

    width: horizontal space allocated for this branch - avoids overlap with other branches

    vert_gap: gap between levels of hierarchy

    vert_loc: vertical location of root

    xcenter: horizontal location of root
    """
    if root is None:
        if isinstance(G, nx.DiGraph):
            root = next(iter(nx.topological_sort(G)))  # allows back compatibility with nx version 1.11
        else:
            random.seed(seed)
            root = random.choice(list(G.nodes))
    visited = set()

    def _hierarchy_pos(G, root, dx, vert_gap, vert_loc, xcenter, pos=None, parent=None):
        """
        see hierarchy_pos docstring for most arguments

        pos: a dict saying where all nodes go if they have been assigned
        parent: parent of this branch. - only affects it if non-directed
        """
        if pos is None:
            pos = {root: (xcenter, vert_loc)}
        else:
            pos[root] = (xcenter, vert_loc)
        children = list(G.neighbors(root))

        visited.add(root)

        nextx = xcenter  # - width / 2 - dx / 2
        for child in children:
            if child in visited:
                continue
            pos = _hierarchy_pos(G, child,
                                 dx=dx,
                                 vert_gap=vert_gap,
                                 vert_loc=vert_loc - vert_gap,
                                 xcenter=nextx,
                                 pos=pos, parent=root)
            nextx += dx

        children = list(G.predecessors(root))
        for child in children:
            if child in visited:
                continue
            pos = _hierarchy_pos(G, child,
                                 dx=dx,
                                 vert_gap=vert_gap,
                                 vert_loc=vert_loc + vert_gap,
                                 xcenter=nextx,
                                 pos=pos, parent=root)
            nextx += dx
        return pos

    return _hierarchy_pos(G, root, dx, vert_gap, vert_loc, xcenter)
