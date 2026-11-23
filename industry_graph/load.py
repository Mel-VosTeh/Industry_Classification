"""Transactional, repeatable upsert of a validated CSV snapshot."""
import argparse
import json
import sys

from neo4j.exceptions import Neo4jError, ServiceUnavailable

from .data import DEFAULT_DATA, read_data
from .db import connection

CONSTRAINT = """CREATE CONSTRAINT classification_identity IF NOT EXISTS
FOR (c:ClassificationCode) REQUIRE (c.system, c.code) IS UNIQUE"""
NODES = """UNWIND $rows AS row
MERGE (c:ClassificationCode {system: row.system, code: row.code})
SET c.name = row.name, c.fictional = true"""
HIERARCHY = """UNWIND $rows AS row
MATCH (p:ClassificationCode {system: row.system, code: row.parent_code})
MATCH (c:ClassificationCode {system: row.system, code: row.child_code})
MERGE (p)-[:PARENT_OF]->(c)"""
MAPPINGS = """UNWIND $rows AS row
MATCH (s:ClassificationCode {system: row.source_system, code: row.source_code})
MATCH (t:ClassificationCode {system: row.target_system, code: row.target_code})
MERGE (s)-[m:MAPS_TO]->(t)
SET m.mapping_type = row.mapping_type, m.provenance = row.provenance,
    m.confidence = row.confidence"""


def load(session, tables):
    from .data import validate
    validate(tables)
    session.run(CONSTRAINT).consume()
    mappings = [dict(row, confidence=float(row["confidence"])
                     if row["confidence"] != "" else None) for row in tables["mappings"]]

    def write(tx):
        for query, rows in ((NODES, tables["codes"]), (HIERARCHY, tables["hierarchy"]),
                            (MAPPINGS, mappings)):
            tx.run(query, rows=rows).consume()
    session.execute_write(write)
    return {name: len(rows) for name, rows in tables.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=DEFAULT_DATA)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        tables = read_data(args.data_dir)
        if args.validate_only:
            print("Valid input: " + json.dumps({k: len(v) for k, v in tables.items()}))
        else:
            with connection() as session:
                print("Upserted input records: " + json.dumps(load(session, tables)))
    except (ValueError, OSError, Neo4jError, ServiceUnavailable) as error:
        print(f"Load failed ({type(error).__name__}): {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
