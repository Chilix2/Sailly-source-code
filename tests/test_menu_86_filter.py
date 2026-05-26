"""Unit test for the menu 86 filter — runs without pytest.

Validates:
  1. With no unavailable items, the menu is returned unchanged.
  2. With one 86'd dish, it's removed (case-insensitive) but siblings remain.
  3. Non-list menu entries are passed through untouched.

Run: ``PYTHONPATH=. python tests/test_menu_86_filter.py``
"""
from __future__ import annotations

import sys


def _import_filter():
    from tools.executor import _filter_86_from_menu
    return _filter_86_from_menu


def test_noop_when_empty():
    f = _import_filter()
    menu = {"hauptgerichte": [{"name": "Bibimbap", "price": 14.9}]}
    assert f(menu, set()) == menu


def test_removes_86d_case_insensitive():
    f = _import_filter()
    menu = {
        "hauptgerichte": [
            {"name": "Bibimbap", "price": 14.9},
            {"name": "Bulgogi", "price": 16.9},
        ],
        "desserts": [{"name": "Mochi-Eis", "price": 5.9}],
    }
    out = f(menu, {"bulgogi"})
    names = [i["name"] for i in out["hauptgerichte"]]
    assert names == ["Bibimbap"], names
    assert len(out["desserts"]) == 1


def test_preserves_non_list_entries():
    f = _import_filter()
    menu = {"meta": "string-not-list", "hauptgerichte": [{"name": "Bibimbap"}]}
    out = f(menu, {"bibimbap"})
    assert out["meta"] == "string-not-list"
    assert out["hauptgerichte"] == []


def _run():
    errs = []
    for t in (test_noop_when_empty, test_removes_86d_case_insensitive, test_preserves_non_list_entries):
        try:
            t()
            print(f"  PASS: {t.__name__}")
        except Exception as e:
            errs.append((t.__name__, repr(e)))
            print(f"  FAIL: {t.__name__} — {e!r}")
    if errs:
        print(f"\n{len(errs)} FAILED")
        sys.exit(1)
    print("\nALL PASS")


if __name__ == "__main__":
    _run()
