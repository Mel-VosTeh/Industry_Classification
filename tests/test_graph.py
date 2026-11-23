from copy import deepcopy

import pytest

from industry_graph.analyze import analyze
from industry_graph.data import ValidationError, read_data, validate


def test_sample_counts():
    data = read_data()
    assert {k: len(v) for k, v in data.items()} == {"codes": 13, "hierarchy": 11, "mappings": 4}


@pytest.mark.parametrize("reference", ["", "UNKNOWN"])
def test_bad_reference(reference):
    data = read_data()
    data["hierarchy"][0]["child_code"] = reference
    with pytest.raises(ValidationError, match="invalid code reference"):
        validate(data)


def test_duplicate_code():
    data = read_data()
    data["codes"].append(deepcopy(data["codes"][0]))
    with pytest.raises(ValidationError, match="duplicate identifier"):
        validate(data)


@pytest.mark.parametrize("value", ["nan", "inf", "-0.1", "1.1", "maybe"])
def test_invalid_confidence(value):
    data = read_data()
    data["mappings"][0]["confidence"] = value
    with pytest.raises(ValidationError, match="confidence"):
        validate(data)


def test_cycle_validation_and_analysis():
    data = read_data()
    data["hierarchy"].append(dict(system="FIC_A", parent_code="A11", child_code="A"))
    with pytest.raises(ValidationError, match="cycle"):
        validate(data)
    a, b = ("X", "a"), ("X", "b")
    assert analyze([a, b], [(a, b), (b, a)], [])["hierarchy_cyclic_groups"] == [["X:a", "X:b"]]
    assert analyze([a], [(a, a)], [])["hierarchy_cyclic_groups"] == [["X:a"]]


def test_mapping_analysis_includes_incoming_and_isolated_codes():
    data = read_data()
    nodes = [(r["system"], r["code"]) for r in data["codes"]]
    mappings = [((r["source_system"], r["source_code"]),
                 (r["target_system"], r["target_code"])) for r in data["mappings"]]
    result = analyze(nodes, [], mappings)
    assert result["unmapped_codes"] == ["FIC_A:A", "FIC_A:A1", "FIC_A:A2", "FIC_A:A22",
                                         "FIC_B:B", "FIC_B:B1", "FIC_B:B2"]
    assert result["mapping_groups"] == [
        ["FIC_A:A11", "FIC_A:A21", "FIC_B:B11", "FIC_B:B21"],
        ["FIC_A:A12", "FIC_B:B12"]]
