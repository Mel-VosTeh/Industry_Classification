"""Read and validate the entire small input dataset before database writes."""
import csv
import math
from pathlib import Path

import networkx as nx

DEFAULT_DATA = Path(__file__).resolve().parents[1] / "data"
FIELDS = {
    "codes": ("system", "code", "name"),
    "hierarchy": ("system", "parent_code", "child_code"),
    "mappings": ("source_system", "source_code", "target_system", "target_code",
                 "mapping_type", "provenance", "confidence"),
}


class ValidationError(ValueError):
    """One or more input records cannot be loaded safely."""


def read_data(directory=DEFAULT_DATA):
    tables, errors = {}, []
    for name, fields in FIELDS.items():
        with (Path(directory) / f"{name}.csv").open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames != list(fields):
                errors.append(f"{name}: expected columns {', '.join(fields)}")
            tables[name] = []
            for line, raw in enumerate(reader, 2):
                if None in raw or any(v is None for v in raw.values()):
                    errors.append(f"{name}:{line}: malformed CSV row")
                    continue
                tables[name].append({k: v.strip() for k, v in raw.items()})
    if errors:
        raise ValidationError("\n".join(errors))
    validate(tables)
    return tables


def validate(tables):
    errors, identifiers = [], set()
    for table, fields in FIELDS.items():
        seen = set()
        for line, row in enumerate(tables[table], 2):
            label = f"{table}:{line}"
            for field in fields:
                if field != "confidence" and not row.get(field):
                    errors.append(f"{label}: missing {field}")
            if table == "codes":
                identity = (row.get("system"), row.get("code"))
                identifiers.add(identity)
            elif table == "hierarchy":
                identity = tuple(row.get(k) for k in fields)
            else:
                # One directed mapping per endpoint pair; type/provenance are mutable properties.
                identity = tuple(row.get(k) for k in fields[:4])
                if row.get("mapping_type") not in {"exact", "broader", "related"}:
                    errors.append(f"{label}: invalid mapping_type")
                if row.get("source_system") == row.get("target_system"):
                    errors.append(f"{label}: mapping must cross systems")
                value = row.get("confidence", "")
                if value != "":
                    try:
                        confidence = float(value)
                        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                            raise ValueError
                    except (ValueError, TypeError):
                        errors.append(f"{label}: confidence must be blank or a number in [0, 1]")
            if identity in seen:
                errors.append(f"{label}: duplicate identifier {identity}")
            seen.add(identity)
    hierarchy = nx.DiGraph()
    hierarchy.add_nodes_from(identifiers)
    for table in ("hierarchy", "mappings"):
        for line, row in enumerate(tables[table], 2):
            if table == "hierarchy":
                ends = [(row.get("system"), row.get(k)) for k in ("parent_code", "child_code")]
                hierarchy.add_edge(*ends)
            else:
                ends = [(row.get(f"{side}_system"), row.get(f"{side}_code"))
                        for side in ("source", "target")]
            for endpoint in ends:
                if endpoint not in identifiers:
                    errors.append(f"{table}:{line}: invalid code reference {endpoint}")
    if not nx.is_directed_acyclic_graph(hierarchy):
        errors.append("hierarchy: directed cycle detected")
    if errors:
        raise ValidationError("\n".join(errors))
