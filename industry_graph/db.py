"""Environment-based connection; never print credentials."""
import os
from contextlib import contextmanager

from dotenv import load_dotenv
from neo4j import GraphDatabase


@contextmanager
def connection():
    load_dotenv()
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise ValueError("Set NEO4J_PASSWORD in .env or the environment")
    with GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                              auth=(os.getenv("NEO4J_USER", "neo4j"), password)) as driver:
        driver.verify_connectivity()
        with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
            yield session
