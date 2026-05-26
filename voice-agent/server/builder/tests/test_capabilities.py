"""Tests for Builder industry capability packs."""

from server.builder.capabilities import list_industry_packs, load_industry_pack


REQUIRED_INDUSTRIES = {
    "restaurant",
    "hospitality",
    "hotel",
    "car_dealership",
    "construction_trades",
    "medical_practice",
    "smb_support",
    "other_custom",
}


def test_required_industry_packs_load():
    pack_ids = {pack["id"] for pack in list_industry_packs()}

    assert REQUIRED_INDUSTRIES.issubset(pack_ids)


def test_capabilities_include_guards_variables_and_mandatory_scenarios():
    for industry in REQUIRED_INDUSTRIES:
        pack = load_industry_pack(industry)

        assert pack.capabilities, f"{industry} has no capabilities"
        for capability in pack.capabilities:
            assert capability.slots or capability.variables, f"{industry}/{capability.id} has no slots or variables"
            assert capability.guards, f"{industry}/{capability.id} has no guards"
            assert capability.scenarios, f"{industry}/{capability.id} has no scenarios"
            assert all(scenario.mandatory for scenario in capability.scenarios), (
                f"{industry}/{capability.id} has non-mandatory scenarios"
            )

            expected_guard_ids = {
                guard_id
                for scenario in capability.scenarios
                for guard_id in scenario.expected.guards
            }
            capability_guard_ids = {guard.id for guard in capability.guards}
            assert expected_guard_ids.issubset(capability_guard_ids), (
                f"{industry}/{capability.id} scenario expects unknown guards: "
                f"{expected_guard_ids - capability_guard_ids}"
            )
"""Tests for Builder capability and scenario-template read helpers."""

from server.builder.capabilities import capabilities_response, scenario_templates_response


def test_capabilities_response_supports_full_pack_dump():
    response = capabilities_response("restaurant")

    pack = response["packs"][0]
    assert pack["id"] == "restaurant"
    assert any(capability["id"] == "takeaway_order" for capability in pack["capabilities"])


def test_scenario_templates_can_filter_by_capability():
    response = scenario_templates_response("restaurant", "takeaway_order")

    templates = response["templates"]
    assert templates
    assert {template["capability"] for template in templates} == {"takeaway_order"}
    assert templates[0]["industry"] == "restaurant"
    assert templates[0]["caller_goal"]
    assert "expected" in templates[0]
