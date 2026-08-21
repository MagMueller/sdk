import httpx

from browser_use_sdk._core.http import _clean_params


def test_clean_params_repeats_sequence_values() -> None:
    cleaned = _clean_params(
        {
            "metadata": ["team", "env=prod"],
            "pageSize": 10,
            "includeUrls": False,
            "cursor": None,
        }
    )
    assert cleaned == {
        "metadata": ["team", "env=prod"],
        "pageSize": "10",
        "includeUrls": "false",
    }
    assert httpx.QueryParams(cleaned).multi_items() == [
        ("metadata", "team"),
        ("metadata", "env=prod"),
        ("pageSize", "10"),
        ("includeUrls", "false"),
    ]
