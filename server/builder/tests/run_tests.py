#!/usr/bin/env python3
"""Simple test runner for graph introspection (no pytest required)."""

import sys
import os

sys.path.insert(0, "/home/charles2/sailly-browser-demo")

from server.builder.graph_introspect import build_graph, list_tenants


def test_build_graph_returns_valid_structure():
    """Verify graph JSON has all required top-level keys."""
    graph = build_graph()
    
    assert "tenant" in graph, "Missing 'tenant' key"
    assert "nodes" in graph, "Missing 'nodes' key"
    assert "edges" in graph, "Missing 'edges' key"
    assert "tools" in graph, "Missing 'tools' key"
    assert "forced_commits" in graph, "Missing 'forced_commits' key"
    
    assert isinstance(graph["nodes"], list)
    assert isinstance(graph["edges"], list)
    assert isinstance(graph["tools"], list)
    assert isinstance(graph["forced_commits"], list)
    
    return True


def test_node_set_complete():
    """All 7 expected nodes are present."""
    graph = build_graph()
    node_ids = {n["id"] for n in graph["nodes"]}
    
    expected = {"greeting", "menu_browse", "ordering", "reservation", "escalation", "faq", "goodbye"}
    assert node_ids == expected, f"Expected {expected}, got {node_ids}"
    
    return True


def test_all_nodes_have_required_fields():
    """Every node must have required fields."""
    graph = build_graph()
    
    for node in graph["nodes"]:
        assert "id" in node, f"Node missing 'id': {node}"
        assert "label" in node
        assert "prompt" in node
        assert "tools" in node
        assert "prerequisites" in node
        assert isinstance(node["tools"], list)
        assert isinstance(node["prerequisites"], dict)
    
    return True


def test_all_edges_target_valid_nodes():
    """Every edge must target an existing node (except [return])."""
    graph = build_graph()
    node_ids = {n["id"] for n in graph["nodes"]}
    
    for edge in graph["edges"]:
        assert "from" in edge, f"Edge missing 'from': {edge}"
        assert "to" in edge, f"Edge missing 'to': {edge}"
        
        # from must be a valid node
        if edge["from"] != "[return]":
            assert edge["from"] in node_ids, f"Edge from {edge['from']} not in nodes {node_ids}"
        
        # to may be [return] or a valid node
        if edge["to"] != "[return]":
            assert edge["to"] in node_ids, f"Edge to {edge['to']} not in nodes {node_ids}"
    
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


def test_forced_commits_tools_exist():
    """Every tool in forced_commits must be valid."""
    graph = build_graph()
    all_tool_names = {t["name"] for t in graph["tools"]}
    
    for step in graph["forced_commits"]:
        for tool in step["tools"]:
            assert tool in all_tool_names, f"Forced-commit tool {tool} not in tool list {all_tool_names}"
    
    return True


def main():
    """Run all tests."""
    tests = [
        ("Graph structure", test_build_graph_returns_valid_structure),
        ("Node set complete", test_node_set_complete),
        ("Node fields", test_all_nodes_have_required_fields),
        ("Edge targets valid", test_all_edges_target_valid_nodes),
        ("Tenants structure", test_list_tenants_returns_valid_structure),
        ("Doboo tenant present", test_doboo_tenant_present),
        ("Forced commits tools exist", test_forced_commits_tools_exist),
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
