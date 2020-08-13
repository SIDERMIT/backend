from sidermit.city.graph import CBD, Periphery, Subcenter


def get_network_descriptor(graph_obj):
    """

    :param graph_obj: sidermite.city.Graph object
    :return: dict with nodes and edges
    """
    nodes = []
    for node_obj in graph_obj.get_nodes():
        node_type = None
        if isinstance(node_obj, CBD):
            node_type = 'cbd'
        elif isinstance(node_obj, Periphery):
            node_type = 'periphery'
        elif isinstance(node_obj, Subcenter):
            node_type = 'subcenter'

        node_descriptor = dict(name=node_obj.name, id=node_obj.id, x=node_obj.x, y=node_obj.y, type=node_type)
        nodes.append(node_descriptor)

    edges = []
    for edge_obj in graph_obj.get_edges():
        edge_descriptor = dict(id=edge_obj.id, source=edge_obj.node1.id, target=edge_obj.node2.id)
        edges.append(edge_descriptor)

    return dict(nodes=nodes, edges=edges)
