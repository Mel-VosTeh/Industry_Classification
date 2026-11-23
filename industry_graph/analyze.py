"""Read Neo4j into separate hierarchy and mapping graphs for batch analysis."""
import json
import sys

import networkx as nx
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from .db import connection


def analyze(codes, hierarchy_edges, mapping_edges):
    hierarchy = nx.DiGraph()
    mappings = nx.Graph()
    hierarchy.add_nodes_from(codes)
    mappings.add_nodes_from(codes)
    hierarchy.add_edges_from(hierarchy_edges)
    mappings.add_edges_from((s, t) for s, t in mapping_edges if s[0] != t[0])
    label = lambda node: f"{node[0]}:{node[1]}"
    groups = [sorted(map(label, group)) for group in nx.connected_components(mappings)
              if len(group) > 1]
    # SCCs identify all cyclic regions without enumerating exponentially many cycles.
    cycles = [sorted(map(label, group)) for group in nx.strongly_connected_components(hierarchy)
              if len(group) > 1 or hierarchy.has_edge(next(iter(group)), next(iter(group)))]
    return {
        "unmapped_codes": sorted(label(n) for n, degree in mappings.degree if degree == 0),
        "mapping_groups": sorted(groups),
        "hierarchy_cyclic_groups": sorted(cycles),
    }


def fetch_and_analyze(tx):
    codes = [(r["system"], r["code"]) for r in tx.run(
        "MATCH (c:ClassificationCode) RETURN c.system AS system, c.code AS code")]
    edges = {}
    for rel in ("PARENT_OF", "MAPS_TO"):
        # Relationship names are fixed constants, not user input.
        edges[rel] = [((r["ss"], r["sc"]), (r["ts"], r["tc"])) for r in tx.run(
            f"MATCH (s:ClassificationCode)-[:{rel}]->(t:ClassificationCode) "
            "RETURN s.system AS ss, s.code AS sc, t.system AS ts, t.code AS tc")]
    return analyze(codes, edges["PARENT_OF"], edges["MAPS_TO"])


def main():
    try:
        with connection() as session:
            print(json.dumps(session.execute_read(fetch_and_analyze), indent=2))
        return 0
    except (ValueError, Neo4jError, ServiceUnavailable) as error:
        print(f"Analysis failed ({type(error).__name__}): {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
