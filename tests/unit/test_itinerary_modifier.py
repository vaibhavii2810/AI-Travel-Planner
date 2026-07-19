"""
Unit tests for the mock-planner NL modification parser.

Confirms the fix for: "the system treats all modifications as adding a new
activity to Day 1 Morning" regardless of what the user actually asked for.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.models.domain import Activity, DailyPlan
from app.services.itinerary_modifier import (
    apply_modification,
    parse_modification_instructions,
)


def _activity(name: str, cost: float = 10.0) -> Activity:
    return Activity(
        name=name,
        description=f"Description of {name}",
        location="Goa, India",
        duration_minutes=60,
        estimated_cost_per_person=cost,
    )


def _make_plans(n: int = 3) -> list[DailyPlan]:
    plans = []
    for i in range(1, n + 1):
        plans.append(
            DailyPlan(
                day_number=i,
                date=date(2025, 12, i),
                theme=f"Day {i} Theme",
                morning=[_activity(f"Day{i} Morning Activity")],
                afternoon=[_activity(f"Day{i} Afternoon Activity")],
                evening=[_activity(f"Day{i} Evening Activity")],
                accommodation="Beach Hotel",
                estimated_daily_cost_per_person=75.0,
                travel_notes=f"Original Day {i} notes",
            )
        )
    return plans


# ── parse_modification_instructions ─────────────────────────────────────────

def test_bracket_target_day_wins():
    intent = parse_modification_instructions("[Target: Day 2] Replace Spice Tour with Dolphin Watching.", num_days=3)
    assert intent.target_day == 2
    assert intent.operation == "replace"
    assert intent.old_text == "Spice Tour"
    assert intent.new_text == "Dolphin Watching"


def test_freeform_day_and_slot_mention():
    intent = parse_modification_instructions("Replace the Day 2 morning activity with a museum.", num_days=3)
    assert intent.target_day == 2
    assert intent.target_slot == "morning"
    assert intent.operation == "replace"
    # generic "activity" placeholder — no real name to match against
    assert intent.old_text is None
    assert intent.new_text == "a museum"


def test_replace_with_no_old_activity_named():
    """Regression: '[Target: Day 1] replace with the street roaming' — a real
    user request where nothing appears between 'replace' and 'with'. Previously
    this failed to match at all and silently fell back to a no-op note."""
    intent = parse_modification_instructions("[Target: Day 1] replace with the street roaming", num_days=3)
    assert intent.target_day == 1
    assert intent.operation == "replace"
    assert intent.old_text is None
    assert intent.new_text == "the street roaming"


def test_replace_with_pronoun_placeholder_treated_as_no_old_activity():
    intent = parse_modification_instructions("[Target: Day 2] Replace it with paragliding.", num_days=3)
    assert intent.operation == "replace"
    assert intent.old_text is None
    assert intent.new_text == "paragliding"


def test_last_day_reference():
    intent = parse_modification_instructions("Add a spa or wellness experience on the last day.", num_days=5)
    assert intent.target_day == 5
    assert intent.operation == "add"


def test_swap_cross_day():
    intent = parse_modification_instructions("Swap the Day 1 morning and Day 2 evening.", num_days=3)
    assert intent.operation == "swap"
    assert intent.target_day == 1
    assert intent.target_slot == "morning"
    assert intent.swap_day2 == 2
    assert intent.swap_slot2 == "evening"


def test_remove_operation():
    intent = parse_modification_instructions("[Target: Day 1] Remove the scuba diving trip.", num_days=3)
    assert intent.target_day == 1
    assert intent.operation == "remove"
    assert intent.old_text == "scuba diving trip"


def test_hotel_update():
    intent = parse_modification_instructions("[Target: Day 1] Replace the hotel with a cheaper option.", num_days=3)
    assert intent.operation == "update_accommodation"
    assert intent.new_text == "a cheaper option"


# ── Holistic Reject feedback (no day dropdown → no day/slot in the text) ────

def test_budget_too_high_is_holistic_reduce_budget():
    intent = parse_modification_instructions("The budget is too high.", num_days=4)
    assert intent.operation == "reduce_budget"
    assert intent.target_day is None


def test_suggest_cheaper_hotels_is_reduce_budget():
    intent = parse_modification_instructions("Please suggest cheaper hotels and transport.", num_days=4)
    assert intent.operation == "reduce_budget"


def test_reduce_the_budget_is_reduce_budget():
    intent = parse_modification_instructions("Please reduce the budget.", num_days=4)
    assert intent.operation == "reduce_budget"


def test_dont_like_activities_is_regenerate_activities():
    intent = parse_modification_instructions("I don't like these activities.", num_days=4)
    assert intent.operation == "regenerate_activities"


def test_budget_not_good_with_explicit_target_extracts_amount():
    """Regression: a real user request — 'not good' isn't in any keyword list,
    but 'budget' + an explicit 'under 900' target must still be recognised."""
    intent = parse_modification_instructions("my budget is not good so make it under 900", num_days=3)
    assert intent.operation == "reduce_budget"
    assert intent.target_budget == 900.0


def test_target_budget_with_currency_symbol_extracted():
    intent = parse_modification_instructions("Please keep the budget under $750.", num_days=3)
    assert intent.operation == "reduce_budget"
    assert intent.target_budget == 750.0


def test_reduce_budget_without_explicit_number_has_no_target():
    intent = parse_modification_instructions("The budget is too high.", num_days=3)
    assert intent.operation == "reduce_budget"
    assert intent.target_budget is None


def test_more_indoor_no_outdoor_detected_as_activity_type():
    intent = parse_modification_instructions(
        "On day one I want more indoor activities, no outdoor activities.", num_days=3
    )
    assert intent.operation == "adjust_activity_type"
    assert intent.activity_preference == "indoor"
    assert intent.target_day == 1


def test_more_outdoor_detected_as_activity_type():
    intent = parse_modification_instructions("I want more outdoor activities, avoid indoor spaces.", num_days=3)
    assert intent.operation == "adjust_activity_type"
    assert intent.activity_preference == "outdoor"
    assert intent.target_day is None


def test_prefer_more_cultural_and_historical_detected_as_culture_category():
    """Regression: a real rejection — 'I prefer more cultural and historical
    experiences on day one' previously matched NOTHING and silently no-op'd."""
    intent = parse_modification_instructions(
        "I prefer more cultural and historical experiences on day one", num_days=3
    )
    assert intent.operation == "adjust_activity_type"
    assert intent.activity_preference == "culture"
    assert intent.target_day == 1


def test_replace_with_museum_is_not_hijacked_by_culture_synonym():
    """Regression: 'museum' is a culture synonym, but 'replace X with a
    museum' is an explicit replace and must NOT be reinterpreted as a vague
    category-preference request."""
    intent = parse_modification_instructions("Replace the Day 2 morning activity with a museum.", num_days=3)
    assert intent.operation == "replace"
    assert intent.new_text == "a museum"


def test_day_targeted_hotel_replace_is_not_shadowed_by_budget_heuristic():
    """A '[Target: Day N]' request must still use the precise single-day
    update_accommodation path, not the holistic reduce_budget path, even
    though it contains the word 'cheaper'."""
    intent = parse_modification_instructions("[Target: Day 1] Replace the hotel with a cheaper option.", num_days=3)
    assert intent.operation == "update_accommodation"
    assert intent.target_day == 1


def test_day_clamped_to_range():
    intent = parse_modification_instructions("[Target: Day 9] Replace X with Y.", num_days=3)
    assert intent.target_day == 3


# ── apply_modification ──────────────────────────────────────────────────────

def test_replace_only_touches_targeted_day_and_slot():
    plans = _make_plans(3)
    intent = parse_modification_instructions(
        "[Target: Day 2] Replace Day2 Afternoon Activity with Dolphin Watching.", num_days=3
    )
    result = apply_modification(plans, intent, destination="Goa, India")

    # Day 2 afternoon changed
    assert result[1].afternoon[0].name == "Dolphin Watching"
    # Day 2 morning/evening untouched
    assert result[1].morning[0].name == "Day2 Morning Activity"
    assert result[1].evening[0].name == "Day2 Evening Activity"
    # Day 1 and Day 3 entirely untouched
    assert result[0].theme == "Day 1 Theme"
    assert result[0].morning[0].name == "Day1 Morning Activity"
    assert result[2].theme == "Day 3 Theme"
    assert result[2].morning[0].name == "Day3 Morning Activity"

    # Original input list must not be mutated (deep copy contract)
    assert plans[1].afternoon[0].name == "Day2 Afternoon Activity"


def test_replace_with_no_old_activity_still_mutates_target_day():
    """End-to-end regression for the real 'replace with the street roaming' request:
    it must actually change Day 1, not silently fall back to a no-op note."""
    plans = _make_plans(2)
    intent = parse_modification_instructions("[Target: Day 1] replace with the street roaming", num_days=2)
    result = apply_modification(plans, intent, destination="Paris, France")

    assert result[0].morning[0].name == "The Street Roaming"
    assert result[0].afternoon[0].name == "Day1 Afternoon Activity"
    assert result[0].evening[0].name == "Day1 Evening Activity"
    assert result[1].theme == "Day 2 Theme"


def test_replace_generic_slot_placeholder_replaces_whole_slot():
    plans = _make_plans(2)
    intent = parse_modification_instructions("Replace the Day 1 evening activity with Paragliding.", num_days=2)
    result = apply_modification(plans, intent, destination="Goa, India")

    assert len(result[0].evening) == 1
    assert result[0].evening[0].name == "Paragliding"
    assert result[0].morning[0].name == "Day1 Morning Activity"
    assert result[0].afternoon[0].name == "Day1 Afternoon Activity"
    assert result[1].theme == "Day 2 Theme"


def test_add_appends_without_removing_existing_activity():
    plans = _make_plans(2)
    intent = parse_modification_instructions("[Target: Day 1] Add a seafood restaurant for dinner.", num_days=2)
    result = apply_modification(plans, intent, destination="Goa, India")

    # dinner keyword → evening slot; original evening activity preserved, new one appended
    assert len(result[0].evening) == 2
    assert result[0].evening[0].name == "Day1 Evening Activity"
    assert "Seafood" in result[0].evening[1].name
    assert result[1].theme == "Day 2 Theme"


def test_remove_deletes_matching_activity_only():
    plans = _make_plans(2)
    intent = parse_modification_instructions("[Target: Day 1] Remove Day1 Morning Activity.", num_days=2)
    result = apply_modification(plans, intent, destination="Goa, India")

    assert result[0].morning == []
    assert result[0].afternoon[0].name == "Day1 Afternoon Activity"
    assert result[1].theme == "Day 2 Theme"


def test_replace_without_day_searches_every_day_for_the_named_activity():
    """Regression: Reject (and Modify's 'All Days' option) never specifies a
    day. 'Replace Spice Tour with X' with NO day named must find whichever
    day Spice Tour actually lives on, not silently no-op on Day 1."""
    plans = _make_plans(3)
    plans[1].afternoon[0].name = "Spice Tour"  # lives on Day 2, not Day 1
    intent = parse_modification_instructions("Replace Spice Tour with Dolphin Watching.", num_days=3)
    assert intent.target_day is None

    result = apply_modification(plans, intent, destination="Goa, India")

    assert result[1].afternoon[0].name == "Dolphin Watching"
    # Day 1 and Day 3 untouched — the search found the real day, not a default
    assert result[0].morning[0].name == "Day1 Morning Activity"
    assert result[2].morning[0].name == "Day3 Morning Activity"


def test_remove_without_day_searches_every_day_for_the_named_activity():
    plans = _make_plans(3)
    plans[2].evening[0].name = "Sunset Cruise"  # lives on Day 3, not Day 1
    intent = parse_modification_instructions("Remove Sunset Cruise.", num_days=3)
    assert intent.target_day is None

    result = apply_modification(plans, intent, destination="Goa, India")

    assert result[2].evening == []
    assert result[0].evening[0].name == "Day1 Evening Activity"
    assert result[1].evening[0].name == "Day2 Evening Activity"


def test_replace_without_day_or_name_defaults_to_day_one():
    plans = _make_plans(3)
    intent = parse_modification_instructions("Replace it with something new.", num_days=3)
    assert intent.target_day is None
    assert intent.old_text is None

    result = apply_modification(plans, intent, destination="Goa, India")

    assert result[0].morning[0].name != "Day1 Morning Activity"
    assert result[1].morning[0].name == "Day2 Morning Activity"
    assert result[2].morning[0].name == "Day3 Morning Activity"


def test_update_accommodation_without_day_applies_to_every_day():
    """A hotel complaint with no day named (always true for Reject) is a
    whole-trip complaint, not just Day 1's."""
    plans = _make_plans(3)
    intent = parse_modification_instructions("Replace the hotel with something nicer.", num_days=3)
    assert intent.target_day is None
    assert intent.operation == "update_accommodation"

    result = apply_modification(plans, intent, destination="Goa, India")

    for day in result:
        assert day.accommodation == "Something Nicer"


def test_swap_exchanges_slots_across_days():
    plans = _make_plans(2)
    intent = parse_modification_instructions("Swap the Day 1 morning and Day 2 evening.", num_days=2)
    result = apply_modification(plans, intent, destination="Goa, India")

    assert result[0].morning[0].name == "Day2 Evening Activity"
    assert result[1].evening[0].name == "Day1 Morning Activity"
    # untouched slots
    assert result[0].afternoon[0].name == "Day1 Afternoon Activity"
    assert result[1].morning[0].name == "Day2 Morning Activity"


def test_update_accommodation_only_changes_targeted_day():
    plans = _make_plans(2)
    intent = parse_modification_instructions("[Target: Day 1] Replace the hotel with a budget hostel.", num_days=2)
    result = apply_modification(plans, intent, destination="Goa, India")

    assert result[0].accommodation == "A Budget Hostel"
    assert result[1].accommodation == "Beach Hotel"


def test_daily_cost_recomputed_after_mutation():
    plans = _make_plans(1)
    original_cost = plans[0].estimated_daily_cost_per_person
    intent = parse_modification_instructions("[Target: Day 1] Add a fancy dinner.", num_days=1)
    result = apply_modification(plans, intent, destination="Goa, India")

    assert result[0].estimated_daily_cost_per_person != original_cost
    expected = round(
        sum(a.estimated_cost_per_person for a in result[0].morning)
        + sum(a.estimated_cost_per_person for a in result[0].afternoon)
        + sum(a.estimated_cost_per_person for a in result[0].evening)
        + 45.0,
        2,
    )
    assert result[0].estimated_daily_cost_per_person == expected


def test_unrecognised_feedback_does_not_fabricate_activity():
    plans = _make_plans(2)
    intent = parse_modification_instructions("[Target: Day 1] This plan feels rushed overall.", num_days=2)
    result = apply_modification(plans, intent, destination="Goa, India")

    # No activity added/removed anywhere — only the note changes
    assert result[0].morning[0].name == "Day1 Morning Activity"
    assert result[0].afternoon[0].name == "Day1 Afternoon Activity"
    assert result[0].evening[0].name == "Day1 Evening Activity"
    assert "This plan feels rushed" in result[0].practical_notes


# ── Holistic Reject operations — apply across EVERY day, not just one ───────

def test_reduce_budget_lowers_cost_on_every_day():
    plans = _make_plans(3)
    intent = parse_modification_instructions("The budget is too high.", num_days=3)
    result = apply_modification(plans, intent, destination="Goa, India")

    for orig_day, new_day in zip(plans, result):
        for slot in ("morning", "afternoon", "evening"):
            orig_cost = getattr(orig_day, slot)[0].estimated_cost_per_person
            new_cost = getattr(new_day, slot)[0].estimated_cost_per_person
            assert new_cost == round(orig_cost * 0.7, 2)
            assert new_cost < orig_cost
        assert new_day.accommodation != "Beach Hotel"

    # Original input must not be mutated
    assert plans[0].morning[0].estimated_cost_per_person == 10.0


def test_reduce_budget_without_target_scales_daily_total_by_same_factor():
    """No explicit number named -> flat ~30% cut, applied to the WHOLE daily
    total (including transport/misc), not just the activity subtotal — so a
    later explicit target ('under 900') is actually reachable."""
    plans = _make_plans(1)
    original_daily_cost = plans[0].estimated_daily_cost_per_person
    intent = parse_modification_instructions("Please reduce the budget.", num_days=1)
    result = apply_modification(plans, intent, destination="Goa, India")

    assert result[0].estimated_daily_cost_per_person == round(original_daily_cost * 0.7, 2)


def test_reduce_budget_with_explicit_target_hits_it():
    """'make it under 900' must actually bring the grand total to <= 900,
    not just apply a generic percentage cut."""
    plans = _make_plans(3)  # 3 days x 75.0/day = 225.0/person, x2 travelers = 450.0 grand total
    intent = parse_modification_instructions("my budget is not good so make it under 300", num_days=3)
    assert intent.target_budget == 300.0

    result = apply_modification(plans, intent, destination="Goa, India", num_travelers=2)

    new_grand_total = round(sum(d.estimated_daily_cost_per_person for d in result) * 2, 2)
    assert new_grand_total <= 300.0


def test_reduce_budget_target_never_increases_cost():
    """If the named target is already above the current total, scale is
    clamped to 1.0 — reduce_budget must never raise the price."""
    plans = _make_plans(1)  # 75.0/person, 1 traveler => grand total 75.0
    intent = parse_modification_instructions("Keep the budget under 10000.", num_days=1)
    result = apply_modification(plans, intent, destination="Goa, India", num_travelers=1)

    assert result[0].estimated_daily_cost_per_person == plans[0].estimated_daily_cost_per_person


def test_reduce_budget_with_pool_swaps_activities_not_just_price():
    """Regression: 'the number is changing but the plans of the day are not
    changing' — with a real catalogue available, reduce_budget must swap in
    genuinely cheaper activities, not just relabel the same ones at a discount."""
    plans = _make_plans(1)
    pool = [
        ("Cheap Walk", "desc", 2.0, 1.0, "sightseeing"),
        ("Mid Museum", "desc", 8.0, 2.0, "culture"),
    ]
    intent = parse_modification_instructions("The budget is too high.", num_days=1)
    result = apply_modification(plans, intent, destination="Goa, India", activity_pool=pool)

    # Original activities (cost=10.0 each) must have been replaced by cheaper pool entries
    assert result[0].morning[0].name != "Day1 Morning Activity"
    assert result[0].morning[0].estimated_cost_per_person < 10.0
    assert result[0].accommodation != "Beach Hotel"


def test_reduce_budget_with_pool_and_target_hits_target():
    plans = _make_plans(2)
    pool = [
        ("Cheap Walk", "desc", 2.0, 1.0, "sightseeing"),
        ("Mid Museum", "desc", 8.0, 2.0, "culture"),
    ]
    intent = parse_modification_instructions("Please make the budget under 100.", num_days=2)
    result = apply_modification(plans, intent, destination="Goa, India", activity_pool=pool, num_travelers=1)

    new_grand_total = round(sum(d.estimated_daily_cost_per_person for d in result), 2)
    assert new_grand_total <= 100.0


def test_adjust_activity_type_prefers_indoor_and_scopes_to_named_day():
    plans = _make_plans(2)
    pool = [
        ("Cozy Museum", "desc", 15.0, 2.0, "culture"),      # indoor
        ("Art Gallery", "desc", 12.0, 1.5, "art"),          # indoor
        ("Mountain Hike", "desc", 20.0, 4.0, "adventure"),  # outdoor
    ]
    # The fixture's activities have no recognisable category, so _infer_category
    # returns None for them and they're left alone — swap only happens for
    # activities the pool can actually classify. Simulate that by using an
    # activity whose name matches a pool entry's outdoor category.
    plans[0].morning[0].name = "Goa — Mountain Hike"

    intent = parse_modification_instructions(
        "[Target: Day 1] I want more indoor activities, no outdoor activities.", num_days=2
    )
    assert intent.operation == "adjust_activity_type"
    assert intent.activity_preference == "indoor"
    assert intent.target_day == 1

    result = apply_modification(plans, intent, destination="Goa, India", activity_pool=pool)

    # Day 1's outdoor activity got swapped for an indoor one
    assert result[0].morning[0].name != "Goa — Mountain Hike"
    # Day 2 is completely untouched (day-scoped, not global)
    assert result[1].morning[0].name == "Day2 Morning Activity"


def test_adjust_activity_type_without_day_applies_to_all_days():
    plans = _make_plans(2)
    pool = [
        ("Cozy Museum", "desc", 15.0, 2.0, "culture"),
        ("Mountain Hike", "desc", 20.0, 4.0, "adventure"),
    ]
    plans[0].morning[0].name = "Goa — Mountain Hike"
    plans[1].afternoon[0].name = "Goa — Mountain Hike"

    intent = parse_modification_instructions("I want more indoor activities, no outdoor activities.", num_days=2)
    assert intent.target_day is None  # no day dropdown in RejectModal => applies everywhere

    result = apply_modification(plans, intent, destination="Goa, India", activity_pool=pool)

    assert result[0].morning[0].name != "Goa — Mountain Hike"
    assert result[1].afternoon[0].name != "Goa — Mountain Hike"


def test_adjust_activity_type_uses_full_pool_when_interests_lack_the_type():
    """If the traveler's own interests are all outdoor, the interest-filtered
    activity_pool has no indoor candidates — full_activity_pool must supply them."""
    plans = _make_plans(1)
    plans[0].morning[0].name = "Goa — Mountain Hike"
    outdoor_only_pool = [("Mountain Hike", "desc", 20.0, 4.0, "adventure")]
    full_pool = outdoor_only_pool + [("Cozy Museum", "desc", 15.0, 2.0, "culture")]

    intent = parse_modification_instructions("more indoor activities please", num_days=1)
    result = apply_modification(
        plans, intent, destination="Goa, India",
        activity_pool=outdoor_only_pool, full_activity_pool=full_pool,
    )

    assert "Museum" in result[0].morning[0].name


def test_adjust_activity_type_caps_swap_to_one_per_day():
    """Regression: 'Add more outdoor activities for an active trip' (a real
    RejectModal example) previously replaced EVERY indoor-category activity
    on EVERY day in one shot — a near-total itinerary wipeout that repeated
    the same handful of items. Must cap to one swap per day."""
    plans = _make_plans(2)
    pool = [
        ("Museum Visit", "desc", 15.0, 2.0, "culture"),
        ("Mountain Hike", "desc", 20.0, 4.0, "adventure"),
        ("Kayaking", "desc", 25.0, 3.0, "nature"),
    ]
    # Make every original activity resolve to the "culture" category so all
    # 3 slots per day would be eligible for swapping if there were no cap.
    for day in plans:
        for slot in ("morning", "afternoon", "evening"):
            getattr(day, slot)[0].name = "Goa — Museum Visit"

    intent = parse_modification_instructions("Add more outdoor activities for an active trip.", num_days=2)
    assert intent.operation == "adjust_activity_type"
    assert intent.activity_preference == "outdoor"
    assert intent.target_day is None

    result = apply_modification(plans, intent, destination="Goa, India", activity_pool=pool, full_activity_pool=pool)

    for day in result:
        unchanged = sum(1 for slot in ("morning", "afternoon", "evening") if getattr(day, slot)[0].name == "Goa — Museum Visit")
        # Exactly 2 of the 3 slots must remain untouched (only 1 swap allowed per day)
        assert unchanged == 2


def test_regenerate_activities_without_pool_only_notes():
    plans = _make_plans(2)
    intent = parse_modification_instructions("I don't like these activities.", num_days=2)
    result = apply_modification(plans, intent, destination="Goa, India")

    # No pool supplied — must not fabricate content, only record feedback
    assert result[0].morning[0].name == "Day1 Morning Activity"
    assert "I don't like these activities" in result[0].practical_notes
    assert "I don't like these activities" in result[1].practical_notes


def test_regenerate_activities_with_pool_replaces_every_day():
    plans = _make_plans(2)
    pool = [
        ("Museum Tour", "desc", 20.0, 2.0, "culture"),
        ("Cooking Class", "desc", 40.0, 3.0, "food"),
        ("Night Market", "desc", 15.0, 2.0, "shopping"),
    ]
    intent = parse_modification_instructions("I don't like these activities.", num_days=2)
    result = apply_modification(plans, intent, destination="Goa, India", activity_pool=pool)

    pool_names = {f"Goa — {name}" for (name, *_rest) in pool}
    for day in result:
        for slot in ("morning", "afternoon", "evening"):
            assert getattr(day, slot)[0].name in pool_names
    # Original day content is gone, replaced by pool content
    assert result[0].morning[0].name != "Day1 Morning Activity"
