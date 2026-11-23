"""Opt-in database test. Uses the sample identities; does not clear the database."""
import os

import pytest

from industry_graph.data import read_data
from industry_graph.db import connection
from industry_graph.load import load
from industry_graph.analyze import fetch_and_analyze

pytestmark = [pytest.mark.integration,
              pytest.mark.skipif(os.getenv("RUN_NEO4J_TESTS") != "1",
                                 reason="Set RUN_NEO4J_TESTS=1 with a dedicated demo database")]


def snapshot(session):
    nodes = [r.data() for r in session.run(
        "MATCH (c:ClassificationCode) WHERE c.system IN ['FIC_A','FIC_B'] "
        "RETURN properties(c) AS node ORDER BY c.system, c.code")]
    edges = [r.data() for r in session.run(
        "MATCH (s:ClassificationCode)-[r:PARENT_OF|MAPS_TO]->(t:ClassificationCode) "
        "WHERE s.system IN ['FIC_A','FIC_B'] AND t.system IN ['FIC_A','FIC_B'] "
        "RETURN s.system AS ss,s.code AS sc,type(r) AS type,t.system AS ts,t.code AS tc,"
        "properties(r) AS properties ORDER BY ss,sc,type,ts,tc")]
    return nodes, edges


def test_repeatable_real_load():
    with connection() as session:
        data = read_data()
        load(session, data)
        first = snapshot(session)
        load(session, data)
        assert snapshot(session) == first
        assert len(first[0]) == 13
        assert len(first[1]) == 15
        assert session.execute_read(fetch_and_analyze)["hierarchy_cyclic_groups"] == []
        assert len(session.execute_read(fetch_and_analyze)["unmapped_codes"]) == 7


def test_documented_cypher_queries():
    from industry_graph.verify import verify_queries
    with connection() as session:
        load(session, read_data())
        result = verify_queries(session)
        assert len(result["unmapped_codes"]) == 7
