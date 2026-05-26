"""Unit tests for Flow Builder graph introspection."""

import pytest
from server.builder.graph_introspect import build_graph, list_tenants


class TestGraphIntrospection:
    """Tests that graph introspection is consistent with brain source."""
    
    def test_build_graph_returns_valid_structure(self):
        """Verify graph JSON has all required top-level keys."""
        graph = build_graph()
        
        assert "tenant" in graph
        assert "nodes" in graph
        assert "edges" in graph
        assert "tools" in graph
        assert "forced_commits" in graph
        
        assert isinstance(graph["nodes"], list)
        assert isinstance(graph["edges"], list)
        assert isinstance(graph["tools"], list)
        assert isinstance(graph["forced_commits"], list)
    
    def test_all_nodes_have_required_fields(self):
        """Every node must have id, label, prompt, tools, prerequisites."""
        graph = build_graph()
        
        for node in graph["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "prompt" in node
            assert "tools" in node
            assert "prerequisites" in node
            assert isinstance(node["tools"], list)
            assert isinstance(node["prerequisites"], dict)
    
    def test_node_set_complete(self):
        """All 7 expected nodes are present."""
        graph = build_graph()
        node_ids = {n["id"] for n in graph["nodes"]}
        
        expected = {"greeting", "menu_browse", "ordering", "reservation", "escalation", "faq", "goodbye"}
        assert node_ids == expected, f"Expected {expected}, got {node_ids}"
    
    def test_all_edges_target_valid_nodes(self):
        """Every edge must target an existing node (except [return])."""
        graph = build_graph()
        node_ids = {n["id"] for n in graph["nodes"]}
        
        for edge in graph["edges"]:
            assert "from" in edge
            assert "to" in edge
            
            # from must be a valid node
            if edge["from"] != "[return]":
                assert edge["from"] in node_ids, f"Edge from {edge['from']} not in nodes"
            
            # to may be [return] or a valid node
            if edge["to"] != "[return]":
                assert edge["to"] in node_ids, f"Edge to {edge['to']} not in nodes"
    
    def test_all_node_tools_exist_in_executor(self):
        """Every tool in a node must have an executor handler."""
        from tools.executor import handlers as executor_handlers
        
        graph = build_graph()
        all_tools = set()
        
        for node in graph["nodes"]:
            for tool in node["tools"]:
                all_tools.add(tool)
        
        for tool in all_tools:
            assert tool in executor_handlers, f"Tool {tool} not in executor handlers"
    
    def test_forced_commits_tools_exist(self):
        """Every tool in forced_commits must be valid and have an executor."""
        from tools.executor import handlers as executor_handlers
        
        graph = build_graph()
        
        for step in graph["forced_commits"]:
            for tool in step["tools"]:
                assert tool in executor_handlers, f"Forced-commit tool {tool} not in executor"
    
    def test_guardian_preconditions_only_for_high_stakes_tools(self):
        """GUARDIAN preconditions should only apply to create_order and create_reservation."""
        graph = build_graph()
        
        # Get tool names that have GUARDIAN preconditions
        guarded_tools = {t["name"] for t in graph["tools"] if t.get("guardian")}
        
        # Should be subset of {create_order, create_reservation}
        valid_guarded = {"create_order", "create_reservation"}
        assert guarded_tools.issubset(valid_guarded), f"Unexpected guarded tools: {guarded_tools - valid_guarded}"
    
    def test_list_tenants_returns_valid_structure(self):
        """Tenants list should have id, name, industry."""
        tenants = list_tenants()
        
        assert isinstance(tenants, list)
        
        if len(tenants) > 0:
            for tenant in tenants:
                assert "id" in tenant
                assert "name" in tenant
                assert "industry" in tenant
    
    def test_doboo_tenant_present(self):
        """The doboo tenant should be available."""
        tenants = list_tenants()
        tenant_ids = {t["id"] for t in tenants}
        
        assert "doboo" in tenant_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
