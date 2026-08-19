from engine.sldgraph.models import ElectricalGraph


def graph_json(graph: ElectricalGraph) -> str:
    return graph.model_dump_json(indent=2)
