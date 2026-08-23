"""TOON formatter edge cases."""

from amazon_lyr.cli_actions import _compact, _kv, _quote, toon_object


def test_quote_rules():
    assert _quote("plain") == "plain"
    assert _quote("-leading-dash") == "-leading-dash"  # not numeric → safe bare
    assert _quote("has:colon") == '"has:colon"'
    assert _quote("a,b") == '"a,b"'
    assert _quote("[bracket]") == '"[bracket]"'
    assert _quote('say "hi"') == '"say \\"hi\\""'
    # A lone backslash is unambiguous bare; escaped only when quoting for other reasons.
    assert _quote("back\\slash") == "back\\slash"
    assert _quote('a"b\\c:d') == '"a\\"b\\\\c:d"'
    assert _quote("line\nbreak") == '"line\\nbreak"'
    assert _quote(" padded ") == '" padded "'
    # Numeric-looking strings must be quoted so roundtrip preserves the type.
    for numeric in ("42", "-5", "4.7", "1e3", "-0.5", "true"):
        assert _quote(numeric) == f'"{numeric}"'


def test_kv_value_types():
    assert _kv("b", True) == "b: true"
    assert _kv("n", 42) == "n: 42"
    assert _kv("none", None) == "none: null"
    assert _kv("s", "ok") == "s: ok"


def test_object_nested_dict_indent():
    out = toon_object({"outer": {"inner": 1}})
    assert out == "outer:\n  inner: 1"


def test_object_tabular_list():
    out = toon_object(
        {
            "items": [
                {"asin": "A", "price": 1},
                {"asin": "B", "price": 2},
            ]
        }
    )
    lines = out.splitlines()
    assert lines[0] == "items[2]{asin,price}:"
    assert lines[1].strip() == "A,1"
    assert lines[2].strip() == "B,2"


def test_object_primitive_and_empty_lists():
    out = toon_object({"tags": ["x", "y"], "empty": []})
    assert "tags[2]: x,y" in out
    assert "empty[0]: " in out


def test_compact_truncates_only_long_known_lists():
    items = [{"i": n} for n in range(20)]
    data = {"results": items, "small": [1, 2], "scalar": "x", "details": {"keep": True}}
    out = _compact(data)
    assert len(out["results"]) == 8
    assert out["small"] == [1, 2]
    assert out["scalar"] == "x"
    assert out["details"] == {"keep": True}
