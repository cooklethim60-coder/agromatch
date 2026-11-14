import rotation


def test_rotation_always_compares_three_or_more_strategies_without_peer():
    result = rotation.compare(
        ["wheat", "barley", "wheat"], None, 420, 18, "loam",
        "farmer-provided", True, 0, 0, 0, ["Save water", "Soil health"]
    )
    assert len(result) >= 3
    assert {x["key"] for x in result} >= {"current", "ai", "drought", "soil"}
    assert all(not x.get("empty") for x in result)
    assert all("stress" in x and "assumptions" in x and "missing" in x for x in result)
    assert all(x["priority_notes"] for x in result)


def test_peer_is_additional_and_unknown_crops_are_ignored():
    result = rotation.compare(
        ["wheat", "unknown"], ["pea", "wheat"], 600, 17, "clay",
        "farmer-tested", False, -10, 1, .2, ["Profit"]
    )
    assert len(result) == 5
    peer = next(x for x in result if x["key"] == "peer")
    assert peer["seq"] == ["pea", "wheat"]
    assert any("not scored" in note for x in result for note in x["priority_notes"])
