# Industry Classification Graph Explorer

A small, locally runnable data engineering portfolio demonstration: represent two
fictional industry classification systems, explore their hierarchies, and inspect
cross-system mappings. It is inspired by the general problem of classification
recommendations. It does not describe a prior employer's implementation or claim
that Neo4j or NetworkX was used in any professional project.

**All codes, systems, mappings, confidence values, and provenance are fictional.**
FIC_A and FIC_B are not official standards. No confidential data is included.

## Problem and scope

Different classification systems organize economic activities differently. A
crosswalk can help an analyst locate candidate categories, inspect supporting
context, and find gaps needing review. This project implements CSV validation,
repeatable loading, traversal queries, and graph analysis. It does not implement
a recommendation algorithm or assess mapping accuracy.

## Structure

```text
compose.yaml                Local Neo4j Community service
.env.example                Connection configuration template
main.py                     Convenience loader entry point
industry_graph/data.py      CSV parsing and validation
industry_graph/db.py        Environment-based connection
industry_graph/load.py      Constraint and transactional upserts
industry_graph/analyze.py   Neo4j extraction and NetworkX analysis
industry_graph/verify.py    Executes and checks the four documented Cypher queries
data/                       Fictional CSV inputs (codes, hierarchy, mappings)
queries/                    Four commented Neo4j Browser query examples
tests/                      Offline tests and opt-in integration test
```

## Graph model and interpretation

A `ClassificationCode` node has `system`, `code`, `name`, and `fictional=true`.
The composite `(system, code)` key has a uniqueness constraint; code strings alone
are not identifiers. CSV codes remain strings, preserving possible leading zeros.

`(parent)-[:PARENT_OF]->(child)` means the child is a narrower category **within
the same system**. A root has no incoming hierarchy edge. Multiple parents are
allowed, but cycles are rejected. The dataset includes two hierarchy levels below
each root.

`(source)-[:MAPS_TO]->(target)` records a directed cross-system assertion. Properties
are `mapping_type`, `provenance`, and optional numeric `confidence` (0–1). A blank
confidence is stored as an absent Neo4j property, not zero. The loader supports one
mapping per directed endpoint pair; another type or provenance updates that mapping.

| Type | Meaning in this fictional crosswalk |
| --- | --- |
| exact | Author asserts equal scope for this direct pair |
| broader | Target covers a broader scope than source |
| related | Activities overlap or relate; no containment or equivalence asserted |

For example, A12 packaging maps to broader B12 sustainable materials. A21 repair
is related to both B21 maintenance and B11 instruments. An indirect path does not
establish equivalence. Neither exact assertions nor confidence values have been
externally verified; confidence is illustrative metadata, not a measured score.
Incoming queries can discover a mapping, but its interpretation always follows
the stored source-to-target direction.

Neo4j persists the property graph and enforces node identity. Cypher demonstrates
interactive database traversal and gap queries. NetworkX reads the graph into
memory for programmatic batch analysis: it uses a separate directed hierarchy
and an undirected mapping graph. This separation prevents mapping edges from
creating false hierarchy cycles. Mapping components ignore direction and type
only to group connected candidates, not to infer interchangeable codes.

## Fedora Linux setup

Use a maintained Fedora release with DNF5, Python 3.11 or newer, Docker Engine,
and the Compose plugin. Allow a few GB of disk space and RAM for Docker and Neo4j.
From this repository's root, install the prerequisites (if needed):

```bash
sudo dnf install -y python3 python3-pip dnf-plugins-core
sudo dnf config-manager addrepo --from-repofile https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
python3 --version
```

These commands follow the [official Docker Fedora installation guide](https://docs.docker.com/engine/install/fedora/).
If another Docker installation already exists, consult that guide about package
conflicts before installing. Commands below use `sudo docker`, so no Docker group
configuration is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
cp .env.example .env
# Edit .env and replace the password with your own local password (8+ characters).
sudo docker compose up -d --wait
sudo docker compose ps
python -m industry_graph.load --validate-only
python -m industry_graph.load
python -m industry_graph.verify
python -m industry_graph.analyze
```

`.env` is ignored by Git. Python reads it automatically; explicitly exported
variables take precedence. Compose uses the same file. Keep `NEO4J_USER=neo4j`
for this Compose service. The pinned image is Neo4j Community
`5.26.33-community-ubi10` in the [official image tag catalog](https://hub.docker.com/_/neo4j/tags),
from the [5.26 LTS series](https://neo4j.com/docs/upgrade-migration-guide/5/version-5/).
Both HTTP (7474) and Bolt (7687) are bound to localhost. A named volume avoids
Fedora SELinux bind-mount complications and preserves database state.

If startup fails, inspect `sudo docker compose logs neo4j`. Changing `.env` does
not change the password of an already initialized database; use its existing
password or deliberately recreate the disposable database volume. Stop without
removing data using `sudo docker compose down`. `sudo docker compose down -v`
**deletes this project's database volume** and provides a fresh start.

The loader can also run as `python main.py`. Use `--data-dir /path/to/csv-directory`
for another dataset with identical headers. It reports validation errors with
file/table and row context and exits nonzero on failure. `--validate-only` needs
no running database. The sample reports 13 codes, 11 hierarchy rows, and 4 mapping
rows. A successful load reports input records upserted, not newly created counts.

The loader creates its constraint separately, then writes all records in one
managed transaction. `MERGE` makes sequential reruns repeatable; mutable names
and mapping metadata are updated. This is an upsert, not snapshot replacement:
removing CSV rows does not delete existing graph data. Run a single loader at a
time; concurrent relationship creation is outside this demonstration's guarantees.

## Run Cypher queries

Open <http://localhost:7474>, sign in with `neo4j` and your `.env` password, and
select database `neo4j`. Each file in `queries/` contains Browser `:param` commands
and a query. Run each `:param` line separately, then execute the query. Browser
commands are not plain Cypher, so do not submit the entire file as one driver query.
Change the parameters to explore other codes.

For an automated check against the fresh sample dataset, run
`python -m industry_graph.verify`. It removes Browser-only `:param` lines,
supplies the documented example parameters, executes the actual query files,
and checks their results. It exits nonzero if any query fails or differs from
the expected sample output.

| File | Example input | Expected result on a fresh sample load |
| --- | --- | --- |
| `01_ancestors.cypher` | FIC_A, A11 | A (Production and services), A1 (Manufacturing) |
| `02_direct_mappings.cypher` | FIC_A, A21 | A21 → B11, related, 0.60; A21 → B21, related, confidence absent; both with fictional provenance |
| `03_mapping_path.cypher` | FIC_A, A11 | A11 → B11 ← B1, using MAPS_TO then incoming PARENT_OF |
| `04_unmapped.cypher` | None | FIC_A: A, A1, A2, A22; FIC_B: B, B1, B2 |

The third query shows that A11 maps to a category under B1. It does not say A11
and B1 are equivalent. Roots and intermediate categories are deliberately included
in the unmapped result: a mapped descendant does not imply a mapped ancestor.

## NetworkX results

`python -m industry_graph.analyze` extracts nodes and edges from Neo4j in a managed
read transaction and prints deterministic JSON. On a fresh sample load:

```json
{
  "unmapped_codes": ["FIC_A:A", "FIC_A:A1", "FIC_A:A2", "FIC_A:A22", "FIC_B:B", "FIC_B:B1", "FIC_B:B2"],
  "mapping_groups": [
    ["FIC_A:A11", "FIC_A:A21", "FIC_B:B11", "FIC_B:B21"],
    ["FIC_A:A12", "FIC_B:B12"]
  ],
  "hierarchy_cyclic_groups": []
}
```

Unmapped checks consider both ends of cross-system mappings. Mapping groups are
non-singleton connected components; isolated nodes appear under unmapped codes.
Cycle analysis returns strongly connected regions with multiple nodes or a self
loop, rather than enumerating every possible cycle. Validated input has no cycles;
this check can detect cycles introduced by subsequent manual database edits.
Cypher answers selected database questions; NetworkX produces reusable batch
results and demonstrates distinct graph algorithms. Some overlap is intentional.

## Tests and verification

```bash
source .venv/bin/activate
python -m pytest -m 'not integration'
# Use only this dedicated demo database with the unmodified sample dataset:
RUN_NEO4J_TESTS=1 python -m pytest -m integration
# Run every test with database tests enabled:
RUN_NEO4J_TESTS=1 python -m pytest
```

Offline tests cover missing/invalid references, duplicate keys, invalid confidence,
cycle rejection and detection (including self loops), incoming mapping coverage,
and isolated codes. The integration test loads the sample twice and compares
node and relationship properties and counts, then checks extracted analysis.
An additional integration test checks all four documented Cypher query files.
The tests do not clear the database; use a fresh dedicated demo instance to avoid
unrelated data affecting expected counts. Default pytest skips it unless opted in;
with the flag set, connection failures fail the test instead of being hidden.

Development environment verification: 11 offline tests passed and CSV validation
passed (13 codes, 11 hierarchy rows, 4 mappings). The two integration tests await
a running Neo4j instance.
Python 3.14 emitted Neo4j driver deprecation warnings about asyncio APIs; these
did not fail the tests.
Docker was unavailable, so image startup, live Cypher execution, database loading,
and the opt-in integration test could not be verified here.

