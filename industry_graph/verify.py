"""Execute the documented query files and check the fresh sample results."""
import json
import sys
from pathlib import Path

from neo4j.exceptions import Neo4jError, ServiceUnavailable

from .db import connection

QUERY_DIR = Path(__file__).resolve().parents[1] / "queries"


def run_query(session, filename, **parameters):
    # Browser :param commands are client commands, not Cypher.
    query = "\n".join(line for line in (QUERY_DIR / filename).read_text().splitlines()
                      if not line.strip().startswith(":param"))
    return list(session.run(query, **parameters))


def verify_queries(session):
    ancestors = run_query(session, "01_ancestors.cypher", system="FIC_A", code="A11")
    if [r["code"] for r in ancestors] != ["A", "A1"]:
        raise ValueError("Ancestor query did not match the sample results")
    mappings = run_query(session, "02_direct_mappings.cypher", system="FIC_A", code="A21")
    actual = [(r["source_code"], r["target_code"], r["mapping_type"], r["confidence"])
              for r in mappings]
    if actual != [("A21", "B11", "related", 0.6), ("A21", "B21", "related", None)]:
        raise ValueError("Direct mapping query did not match the sample results")
    paths = run_query(session, "03_mapping_path.cypher", system="FIC_A", code="A11")
    if len(paths) != 1 or [n["code"] for n in paths[0]["path"].nodes] != ["A11", "B11", "B1"]:
        raise ValueError("Mapping path query did not match the sample results")
    unmapped = run_query(session, "04_unmapped.cypher")
    actual_unmapped = [f'{r["system"]}:{r["code"]}' for r in unmapped]
    expected = ["FIC_A:A", "FIC_A:A1", "FIC_A:A2", "FIC_A:A22", "FIC_B:B", "FIC_B:B1", "FIC_B:B2"]
    if actual_unmapped != expected:
        raise ValueError("Unmapped query did not match the sample results")
    return {"ancestors": [r.data() for r in ancestors],
            "direct_mappings": [r.data() for r in mappings],
            "mapping_path_codes": ["A11", "B11", "B1"],
            "unmapped_codes": actual_unmapped}


def main():
    try:
        with connection() as session:
            print(json.dumps(verify_queries(session), indent=2))
        print("All four documented Cypher queries matched the sample results.")
        return 0
    except (ValueError, OSError, Neo4jError, ServiceUnavailable) as error:
        print(f"Query verification failed ({type(error).__name__}): {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
