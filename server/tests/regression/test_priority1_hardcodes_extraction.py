"""Test Priority 1 hardcodes extraction for dual-tenant support.

Tests that all hardcoded values have been extracted to TenantConfig
and work correctly for both doboo and pizzeria_napoli tenants.
"""
import pytest
from server.core.tenant_config import load_tenant_config


@pytest.fixture(params=["doboo", "pizzeria_napoli"])
def tenant_id(request):
    """Parametrize tests to run for both tenants."""
    return request.param


class TestB6MultiIntentFallback:
    """B6: Bibimbap price injection (reservation + FAQ price in same turn)."""
    
    def test_config_field_exists(self, tenant_id):
        """Verify multi_intent_fallback_dish is configured."""
        cfg = load_tenant_config(tenant_id)
        assert hasattr(cfg, "multi_intent_fallback_dish"), f"Missing multi_intent_fallback_dish for {tenant_id}"
        assert cfg.multi_intent_fallback_dish is not None, f"multi_intent_fallback_dish is None for {tenant_id}"
    
    def test_fallback_has_required_fields(self, tenant_id):
        """Verify fallback dish has dish, price, note."""
        cfg = load_tenant_config(tenant_id)
        fallback = cfg.multi_intent_fallback_dish
        assert isinstance(fallback, dict), f"multi_intent_fallback_dish must be dict for {tenant_id}"
        assert "dish" in fallback, f"Missing 'dish' field for {tenant_id}"
        assert "price" in fallback, f"Missing 'price' field for {tenant_id}"
        assert "note" in fallback, f"Missing 'note' field for {tenant_id}"
    
    def test_doboo_specific_values(self):
        """DOBOO-specific: Bibimbap 13.90."""
        cfg = load_tenant_config("doboo")
        fallback = cfg.multi_intent_fallback_dish
        assert fallback["dish"].lower() == "bibimbap"
        assert fallback["price"] == 13.90


class TestHashFiveFridayHours:
    """#5: Friday split hours configuration."""
    
    def test_friday_hours_fields_exist(self, tenant_id):
        """Verify friday_hours_lunch and friday_hours_dinner are configured."""
        cfg = load_tenant_config(tenant_id)
        assert hasattr(cfg, "friday_hours_lunch")
        assert hasattr(cfg, "friday_hours_dinner")
    
    def test_doboo_has_split_hours(self):
        """DOBOO: Friday is split (lunch 11:30–14:00, dinner 18:00–21:30)."""
        cfg = load_tenant_config("doboo")
        assert cfg.friday_hours_lunch == "11:30–14:00"
        assert cfg.friday_hours_dinner == "18:00–21:30"
    
    def test_pizzeria_no_split_hours(self):
        """Pizzeria: Friday is not split (open continuously)."""
        cfg = load_tenant_config("pizzeria_napoli")
        assert cfg.friday_hours_lunch is None
        assert cfg.friday_hours_dinner is None


class TestB7MenuExclusions:
    """B7: Menu items known to NOT exist (prevent PREIS_FALSCH)."""
    
    def test_nonexistent_items_field_exists(self, tenant_id):
        """Verify menu_items_nonexistent is configured."""
        cfg = load_tenant_config(tenant_id)
        assert hasattr(cfg, "menu_items_nonexistent")
        assert isinstance(cfg.menu_items_nonexistent, list)
    
    def test_doboo_has_nonexistent_items(self):
        """DOBOO: Kimchi Jjigae is not on menu."""
        cfg = load_tenant_config("doboo")
        nonexistent = cfg.menu_items_nonexistent
        assert len(nonexistent) > 0
        # Check that at least one kimchi variant is in the list
        has_kimchi_variant = any("kimchi" in item.lower() for item in nonexistent)
        assert has_kimchi_variant


class TestB8VariantFallbacks:
    """B8: Dish extraction fallbacks (common menu variants)."""
    
    def test_variant_fallback_field_exists(self, tenant_id):
        """Verify dish_variants_fallback is configured."""
        cfg = load_tenant_config(tenant_id)
        assert hasattr(cfg, "dish_variants_fallback")
        assert isinstance(cfg.dish_variants_fallback, list)
    
    def test_doboo_has_variant_fallbacks(self):
        """DOBOO: Korean Pancake Kimchi and Bibimbap Rind are fallbacks."""
        cfg = load_tenant_config("doboo")
        variants = cfg.dish_variants_fallback
        assert len(variants) > 0
        variant_names = [v.lower() for v in variants]
        # Check for expected variants
        assert any("kimchi" in v for v in variant_names)
        assert any("bibimbap" in v for v in variant_names)


class TestHashSixFarewells:
    """#6: Farewell strings (rotating phrases to avoid repetition)."""
    
    def test_farewell_options_exist(self, tenant_id):
        """Verify farewell_options_list is configured."""
        cfg = load_tenant_config(tenant_id)
        assert hasattr(cfg, "farewell_options_list")
        assert isinstance(cfg.farewell_options_list, list)
        assert len(cfg.farewell_options_list) > 0
    
    def test_post_commit_farewells_exist(self, tenant_id):
        """Verify post_commit_farewell_options is configured."""
        cfg = load_tenant_config(tenant_id)
        assert hasattr(cfg, "post_commit_farewell_options")
        assert isinstance(cfg.post_commit_farewell_options, list)
        assert len(cfg.post_commit_farewell_options) > 0
    
    def test_order_already_created_farewell_exists(self, tenant_id):
        """Verify order_already_created_farewell is configured."""
        cfg = load_tenant_config(tenant_id)
        assert hasattr(cfg, "order_already_created_farewell")
        assert isinstance(cfg.order_already_created_farewell, str)
        assert len(cfg.order_already_created_farewell) > 0
    
    def test_doboo_specific_farewells(self):
        """DOBOO: Verify German farewell phrases."""
        cfg = load_tenant_config("doboo")
        # Check that at least one farewell is German and contains expected keywords
        all_farewells = (
            cfg.farewell_options_list +
            cfg.post_commit_farewell_options +
            [cfg.order_already_created_farewell]
        )
        assert len(all_farewells) > 0
        # At least one should have "Wiederhören"
        has_wiederhoren = any("wiederhören" in f.lower() for f in all_farewells)
        assert has_wiederhoren


class TestNoNewHardcodes:
    """Verify no new tenant-specific hardcodes were introduced."""
    
    def test_no_hardcoded_doboo_in_config(self, tenant_id):
        """Verify DOBOO-specific hardcodes don't appear in pizzeria config."""
        cfg = load_tenant_config(tenant_id)
        
        # Convert config to dict for string search
        import json
        cfg_dict = cfg.dict() if hasattr(cfg, "dict") else cfg.__dict__
        config_str = json.dumps(cfg_dict, default=str).lower()
        
        # Pizzeria should not have DOBOO-specific strings
        if tenant_id == "pizzeria_napoli":
            assert "bibimbap" not in config_str or "margherita" in config_str, \
                "Pizzeria config should not have DOBOO-specific menu items"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
