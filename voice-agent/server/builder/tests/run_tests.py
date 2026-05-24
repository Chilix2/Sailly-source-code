#!/usr/bin/env python3
"""Simple test runner for graph introspection (no pytest required)."""

import sys
import os

sys.path.insert(0, "/home/charles2/sailly-browser-demo")

from server.builder.graph_introspect import build_graph, list_tenants
from server.builder.graph_foundation import export_v4_graph, validate_graph_document


def test_build_graph_returns_valid_structure():
    """Verify graph JSON has all required top-level keys."""
    graph = build_graph()

    required_keys = {
        "tenant",
        "schema_version",
        "profiles",
        "workers",
        "intent_edges",
        "tool_catalog",
        "commit_gates",
        "guardian_rules",
        "layers",
    }
    missing = required_keys - set(graph)
    assert not missing, f"Missing graph keys: {sorted(missing)}"

    for key in required_keys - {"tenant", "schema_version"}:
        assert isinstance(graph[key], list), f"Graph key {key} should be a list"

    return True


def test_profile_set_complete():
    """Core v4 routing profiles are present."""
    graph = build_graph()
    profile_ids = {profile["id"] for profile in graph["profiles"]}

    expected = {"greeting", "business_info", "order_start", "reservation_start", "goodbye"}
    missing = expected - profile_ids
    assert not missing, f"Missing expected profiles: {sorted(missing)}"

    return True


def test_profiles_have_required_fields():
    """Every profile must expose routing, worker, and tool metadata."""
    graph = build_graph()

    for profile in graph["profiles"]:
        assert "id" in profile, f"Profile missing 'id': {profile}"
        assert "label" in profile
        assert "required_workers" in profile
        assert "optional_workers" in profile
        assert "scheduled_tools" in profile
        assert isinstance(profile["required_workers"], list)
        assert isinstance(profile["optional_workers"], list)
        assert isinstance(profile["scheduled_tools"], list)

    return True


def test_intent_edges_target_valid_profiles():
    """Every intent edge should target a known profile node."""
    graph = build_graph()
    profile_targets = {f"profile_{profile['id']}" for profile in graph["profiles"]}

    for edge in graph["intent_edges"]:
        assert "from" in edge, f"Edge missing 'from': {edge}"
        assert "to" in edge, f"Edge missing 'to': {edge}"
        assert edge["to"] in profile_targets, f"Edge target {edge['to']} not in profiles {profile_targets}"

    return True


def test_list_tenants_returns_valid_structure():
    """Tenants list should have id, name, industry."""
    tenants = list_tenants()
    
    assert isinstance(tenants, list), "Tenants should be a list"
    
    if len(tenants) > 0:
        for tenant in tenants:
            assert "id" in tenant, f"Tenant missing 'id': {tenant}"
            assert "name" in tenant
            assert "industry" in tenant
    
    return True


def test_doboo_tenant_present():
    """The doboo tenant should be available."""
    tenants = list_tenants()
    tenant_ids = {t["id"] for t in tenants}
    
    assert "doboo" in tenant_ids, f"'doboo' not in tenants {tenant_ids}"
    
    return True


def test_commit_gate_tools_exist():
    """Every commit gate references a known tool."""
    graph = build_graph()
    all_tool_names = {tool["name"] for tool in graph["tool_catalog"]}

    for gate in graph["commit_gates"]:
        tool = gate["tool"]
        assert tool in all_tool_names, f"Commit-gate tool {tool} not in tool catalog {all_tool_names}"

    return True


def test_config_graph_export_validates():
    """The lab-safe config graph export has no dangling references."""
    document = export_v4_graph("doboo")
    errors = validate_graph_document(document)
    assert not errors, f"Config graph validation errors: {errors}"

    return True


def main():
    """Run all tests."""
    tests = [
        ("Graph structure", test_build_graph_returns_valid_structure),
        ("Profile set complete", test_profile_set_complete),
        ("Profile fields", test_profiles_have_required_fields),
        ("Intent edge targets valid", test_intent_edges_target_valid_profiles),
        ("Tenants structure", test_list_tenants_returns_valid_structure),
        ("Doboo tenant present", test_doboo_tenant_present),
        ("Commit-gate tools exist", test_commit_gate_tools_exist),
        ("Config graph export validates", test_config_graph_export_validates),
    ]
    
    passed = 0
    failed = 0
    
    print("=" * 70)
    print("Phase 1 Backend Tests")
    print("=" * 70)
    
    for name, test_fn in tests:
        try:
            result = test_fn()
            print(f"✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: {type(e).__name__}: {e}")
            failed += 1
    
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
