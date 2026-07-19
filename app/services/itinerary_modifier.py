"""
Natural-language modification parser for the mock planner agent.

Parses free-text HITL "modify" feedback (as sent by ModifyModal, including its
`[Target: Day N]` prefix) into a structured intent, then applies that intent to
a *copy* of the previous draft itinerary — mutating only the day/slot/activity
that was actually asked for, leaving every other day and slot untouched.

Only used by the mock planner in app.main (active when no real OPENAI_API_KEY
is configured). The real LLM planner handles this via prompt engineering —
see app/prompts/planner_agent.py's MODIFICATION_REVISION_SECTION.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.domain import Activity, DailyPlan

_SLOTS = ("morning", "afternoon", "evening")

_BRACKET_DAY_RE = re.compile(r"\[target:\s*day\s*(\d+)\]", re.IGNORECASE)
_DAY_MENTION_RE = re.compile(r"\bday\s*(\d+)\b", re.IGNORECASE)
_DAY_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_DAY_WORD_MENTION_RE = re.compile(
    r"\bday\s+(" + "|".join(_DAY_WORDS) + r")\b", re.IGNORECASE
)
_SLOT_RE = re.compile(r"\b(morning|afternoon|evening)\b", re.IGNORECASE)
_LAST_DAY_RE = re.compile(r"\blast\s+day\b", re.IGNORECASE)

_SWAP_CROSS_DAY_RE = re.compile(
    r"\bswap\b.*?\bday\s*(\d+)\b(?:\s*(morning|afternoon|evening))?.*?\band\b.*?"
    r"\bday\s*(\d+)\b(?:\s*(morning|afternoon|evening))?",
    re.IGNORECASE | re.DOTALL,
)
_REPLACE_RE = re.compile(
    r"\b(?:replace|swap)\s+(?:the\s+)?(.*?)\s*(?:with|for)\s+(.+?)(?:[.\n]|$)",
    re.IGNORECASE,
)
_GENERIC_OLD_TEXT_RE = re.compile(r"^(?:it|this|that|them|the activity|the activities)$", re.IGNORECASE)
_REMOVE_RE = re.compile(
    r"\b(?:remove|delete|drop|cancel)\s+(?:the\s+)?(.+?)(?:[.\n]|$)",
    re.IGNORECASE,
)
_ADD_RE = re.compile(
    r"\b(?:add|include|insert)\s+(?:a\s+|an\s+|the\s+)?(.+?)(?:[.\n]|$)",
    re.IGNORECASE,
)

_HOTEL_WORDS = ("hotel", "accommodation", "lodging")
_MEAL_SLOT_HINTS = {
    "breakfast": "morning",
    "brunch": "morning",
    "lunch": "afternoon",
    "dinner": "evening",
    "restaurant": "evening",
    "supper": "evening",
}

# ── Holistic (no specific day/slot) feedback — this is what RejectModal always
# sends, since it has no day dropdown: "The budget is too high", "I don't like
# these activities". These apply across the WHOLE itinerary, not one slot.
_BUDGET_CONTEXT_WORDS = ("budget", "cost", "price", "afford", "pricey", "expensive")
_REDUCE_SENTIMENT_WORDS = (
    "reduce", "lower", "cheap", "less", "decrease", "too high", "too much",
    "tighter", "smaller", "not good", "not okay", "not ok", "isn't good",
    "is not good", "bad", "unhappy", "too expensive", "over budget", "overbudget",
)
# An explicit number after under/below/max/etc is itself a strong signal,
# regardless of which sentiment words are present — "make it under 900".
_TARGET_AMOUNT_RE = re.compile(
    r"(?:under|below|less than|no more than|not (?:more than|over)|"
    r"max(?:imum)?(?:\s+of)?|within|up to)\s*[₹$€£]?\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)
_DISLIKE_ACTIVITY_RE = re.compile(
    r"\b(?:don'?t|do not)\s+(?:like|enjoy|love)\b.*\bactiv|\bdislike\b.*\bactiv|\bactiv\w*\b.*\b(?:boring|bad|poor)\b",
    re.IGNORECASE | re.DOTALL,
)

# ── Indoor/outdoor activity-type preference ─────────────────────────────────
# Category-level approximation (this is a mock catalogue, not real venue data):
# nature/adventure/sightseeing skew outdoor; food/shopping/nightlife/culture/art
# skew indoor (dining, museums, malls, bars, galleries).
CATEGORY_IS_OUTDOOR = {
    "food": False, "shopping": False, "nightlife": False,
    "culture": False, "art": False,
    "nature": True, "adventure": True, "sightseeing": True,
}
# Require adjacency to an actual preference word ("more/prefer/want/only/
# need/love", or a "no/avoid/less" negation) — a bare category word anywhere
# in the text is NOT enough. Without this, "replace the tour with a museum"
# would misfire as a "more culture" preference just because "museum" appears
# as the NEW activity's name, hijacking what should be a literal replace.
_PREFERENCE_LEAD = r"(?:more|prefer(?:s|red)?|want(?:s|ed)?|only|need(?:s|ed)?|love[sd]?)"
_NEGATION_LEAD = r"(?:no|not|avoid(?:ing)?|less|fewer)"
_WORD_GAP = r"(?:\w+\s+){0,2}"  # up to 2 filler words, e.g. "more X activities"

_INDOOR_POSITIVE_RE = re.compile(rf"\b{_PREFERENCE_LEAD}\s+{_WORD_GAP}indoor\b", re.IGNORECASE)
_OUTDOOR_POSITIVE_RE = re.compile(rf"\b{_PREFERENCE_LEAD}\s+{_WORD_GAP}outdoor\b", re.IGNORECASE)
_NEGATED_INDOOR_RE = re.compile(rf"\b{_NEGATION_LEAD}\s+{_WORD_GAP}indoor\b", re.IGNORECASE)
_NEGATED_OUTDOOR_RE = re.compile(rf"\b{_NEGATION_LEAD}\s+{_WORD_GAP}outdoor\b", re.IGNORECASE)


def _detect_activity_type_preference(text: str) -> str | None:
    """
    'more indoor activities, no outdoor activities' -> 'indoor'
    'more outdoor, avoid indoor spaces' -> 'outdoor'
    Wanting one type and rejecting the other are treated as the same signal.
    """
    prefer_indoor = bool(_INDOOR_POSITIVE_RE.search(text)) or bool(_NEGATED_OUTDOOR_RE.search(text))
    prefer_outdoor = bool(_OUTDOOR_POSITIVE_RE.search(text)) or bool(_NEGATED_INDOOR_RE.search(text))

    if prefer_indoor and not prefer_outdoor:
        return "indoor"
    if prefer_outdoor and not prefer_indoor:
        return "outdoor"
    return None


# ── Any-category preference — generalizes indoor/outdoor to the other 6
# catalogue categories, since "I prefer more cultural and historical
# experiences" is exactly as valid a Reject reason as "more outdoor".
_CATEGORY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "culture": ("cultural", "historical", "heritage", "museum", "history"),
    "food": ("foodie", "culinary", "cuisine", "dining", "gastronomic"),
    "adventure": ("adventurous", "adrenaline", "thrill", "extreme"),
    "shopping": ("shopping", "retail", "boutique"),
    "nightlife": ("nightlife", "party", "clubbing"),
    "sightseeing": ("sightseeing", "scenic", "landmark"),
    "art": ("artsy", "gallery", "artistic", "creative"),
    "nature": ("outdoorsy", "wildlife", "hiking"),
}


def _detect_category_preference(text: str) -> str | None:
    """Indoor/outdoor bucket takes priority (it's the more specific, explicit
    signal); otherwise look for a specific category synonym, still requiring
    adjacency to a genuine preference word (see _PREFERENCE_LEAD above)."""
    bucket = _detect_activity_type_preference(text)
    if bucket:
        return bucket
    for category, synonyms in _CATEGORY_SYNONYMS.items():
        for word in synonyms:
            if re.search(rf"\b{_PREFERENCE_LEAD}\s+{_WORD_GAP}{re.escape(word)}\b", text, re.IGNORECASE):
                return category
    return None


def _extract_target_budget(text: str) -> float | None:
    match = _TARGET_AMOUNT_RE.search(text)
    if not match:
        return None
    try:
        value = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    return value if value > 0 else None


def _is_budget_reduction_request(text: str) -> bool:
    lower = text.lower()
    if "cheaper" in lower:
        return True
    has_budget_context = any(w in lower for w in _BUDGET_CONTEXT_WORDS)
    has_reduce_sentiment = any(w in lower for w in _REDUCE_SENTIMENT_WORDS)
    if has_budget_context and has_reduce_sentiment:
        return True
    # "budget ... under 900" / "keep cost under 900" — a target number next to
    # budget context is unambiguous even without a sentiment word matching.
    if has_budget_context and _extract_target_budget(text) is not None:
        return True
    return False


def _is_activity_dislike_request(text: str) -> bool:
    lower = text.lower()
    if _DISLIKE_ACTIVITY_RE.search(text):
        return True
    return ("don't like" in lower or "do not like" in lower or "dislike" in lower) and "activit" in lower


@dataclass
class ModificationIntent:
    raw_text: str
    # note | replace | add | remove | swap | update_accommodation |
    # reduce_budget | regenerate_activities | adjust_activity_type
    operation: str = "note"
    target_day: int | None = None          # 1-indexed; None means "every day"
    target_slot: str | None = None         # morning | afternoon | evening
    old_text: str | None = None
    new_text: str | None = None
    swap_day2: int | None = None
    swap_slot2: str | None = None
    target_budget: float | None = None     # explicit "under 900" style target, if named
    activity_preference: str | None = None  # "indoor" | "outdoor"


def _clamp_day(day: int, num_days: int) -> int:
    return max(1, min(day, num_days))


def parse_modification_instructions(text: str, num_days: int) -> ModificationIntent:
    """Best-effort parse of a HITL modify instruction into a structured intent."""
    intent = ModificationIntent(raw_text=text)
    if not text or num_days < 1:
        return intent

    # ── Cross-day swap: "Swap the Day 1 morning and Day 2 evening" ──────────
    swap_match = _SWAP_CROSS_DAY_RE.search(text)
    if swap_match:
        d1, s1, d2, s2 = swap_match.groups()
        intent.operation = "swap"
        intent.target_day = _clamp_day(int(d1), num_days)
        intent.target_slot = (s1 or "morning").lower()
        intent.swap_day2 = _clamp_day(int(d2), num_days)
        intent.swap_slot2 = (s2 or intent.target_slot).lower()
        return intent

    # ── Target day: explicit "[Target: Day N]" bracket wins over free text ──
    # (also accepts spelled-out numbers: "on day one" -> day 1)
    bracket_match = _BRACKET_DAY_RE.search(text)
    day_mention_match = _DAY_MENTION_RE.search(text)
    day_word_match = _DAY_WORD_MENTION_RE.search(text)
    last_day_match = _LAST_DAY_RE.search(text)
    names_a_specific_day = bool(bracket_match or day_mention_match or day_word_match or last_day_match)

    if bracket_match:
        intent.target_day = _clamp_day(int(bracket_match.group(1)), num_days)
    elif last_day_match:
        intent.target_day = num_days
    elif day_mention_match:
        intent.target_day = _clamp_day(int(day_mention_match.group(1)), num_days)
    elif day_word_match:
        intent.target_day = _clamp_day(_DAY_WORDS[day_word_match.group(1).lower()], num_days)

    # ── Target slot: first explicit morning/afternoon/evening mention ───────
    slot_match = _SLOT_RE.search(text)
    if slot_match:
        intent.target_slot = slot_match.group(1).lower()

    # ── Category preference (indoor/outdoor bucket, or a specific category
    # like culture/food/adventure) — works BOTH day-scoped ("[Target: Day 1]
    # more indoor activities") and holistic ("I prefer more cultural and
    # historical experiences" via Reject, which has no day dropdown so
    # target_day stays None => applies across every day).
    activity_pref = _detect_category_preference(text)
    if activity_pref:
        intent.operation = "adjust_activity_type"
        intent.activity_preference = activity_pref
        return intent

    # No day named at all → this is holistic feedback (always true for Reject,
    # since its modal has no day dropdown). Check budget/dislike sentiment
    # BEFORE the day-specific patterns below, which wouldn't match anyway.
    if not names_a_specific_day:
        if _is_budget_reduction_request(text):
            intent.operation = "reduce_budget"
            intent.target_budget = _extract_target_budget(text)
            return intent
        if _is_activity_dislike_request(text):
            intent.operation = "regenerate_activities"
            return intent

    # ── Hotel / accommodation swap takes priority over generic replace ──────
    if any(w in text.lower() for w in _HOTEL_WORDS):
        replace_match = _REPLACE_RE.search(text)
        if replace_match:
            intent.operation = "update_accommodation"
            intent.new_text = replace_match.group(2).strip()
            return intent

    # ── Replace / swap-in-place: "replace X with Y", "swap X for Y", ────────
    # or just "replace with Y" / "swap for Y" (no old activity named at all).
    replace_match = _REPLACE_RE.search(text)
    if replace_match:
        intent.operation = "replace"
        old = replace_match.group(1).strip()
        intent.new_text = replace_match.group(2).strip()
        # Empty capture, or a generic placeholder ("it", "the activity", ...)
        # means no real activity name to match against — fall back to
        # slot-only targeting instead of leaving the request unapplied.
        if (
            not old
            or _GENERIC_OLD_TEXT_RE.match(old)
            or (re.search(r"\bactivit(?:y|ies)\b", old, re.IGNORECASE) and len(old.split()) <= 6)
        ):
            intent.old_text = None
        else:
            intent.old_text = old
        return intent

    # ── Remove: "remove X", "delete X" ───────────────────────────────────────
    remove_match = _REMOVE_RE.search(text)
    if remove_match:
        intent.operation = "remove"
        intent.old_text = remove_match.group(1).strip()
        return intent

    # ── Add: "add X", "include X" ────────────────────────────────────────────
    add_match = _ADD_RE.search(text)
    if add_match:
        intent.operation = "add"
        intent.new_text = add_match.group(1).strip()
        if intent.target_slot is None:
            lower = text.lower()
            for word, slot in _MEAL_SLOT_HINTS.items():
                if word in lower:
                    intent.target_slot = slot
                    break
        return intent

    return intent


def _activity_matches(activity: Activity, query: str) -> bool:
    if not query:
        return False
    q = query.lower().strip()
    name = activity.name.lower()
    if q in name or name in q:
        return True
    q_tokens = {w for w in re.findall(r"[a-z']+", q) if len(w) > 3}
    n_tokens = {w for w in re.findall(r"[a-z']+", name) if len(w) > 3}
    return bool(q_tokens & n_tokens)


def _infer_category(activity_name: str, activity_pool: list[tuple]) -> str | None:
    """Activity.name is built as 'City — Catalogue Name'; map it back to the
    catalogue entry to recover its category (food/nature/adventure/etc)."""
    short_name = activity_name.split("—", 1)[-1].strip().lower() if "—" in activity_name else activity_name.lower()
    for (name, _desc, _cost, _hours, cat) in activity_pool:
        if name.lower() == short_name:
            return cat
    return None


def _find_slot_with_activity(day: DailyPlan, query: str) -> str | None:
    for slot in _SLOTS:
        for activity in getattr(day, slot):
            if _activity_matches(activity, query):
                return slot
    return None


def _resolve_target_day_index(intent: ModificationIntent, plans: list[DailyPlan]) -> int:
    """0-based day index for replace/remove. If a day was named, use it.
    Otherwise (always true for Reject, and for Modify's "All Days" option)
    search every day for the named activity — defaulting to Day 1 only when
    there's no name to search for at all."""
    if intent.target_day:
        return max(0, min(intent.target_day - 1, len(plans) - 1))
    if intent.old_text:
        for idx, day in enumerate(plans):
            if _find_slot_with_activity(day, intent.old_text):
                return idx
    return 0


def _recompute_day_cost(day: DailyPlan) -> None:
    total = sum(a.estimated_cost_per_person for a in day.morning)
    total += sum(a.estimated_cost_per_person for a in day.afternoon)
    total += sum(a.estimated_cost_per_person for a in day.evening)
    day.estimated_daily_cost_per_person = round(total + 45.0, 2)  # +45 flat transport/misc, matches initial generation


def _new_activity(name: str, destination: str, note: str) -> Activity:
    return Activity(
        name=(name or "Custom Activity").strip().title(),
        description=f"Added per your request: {note[:150]}",
        location=destination,
        duration_minutes=120,
        estimated_cost_per_person=25.0,
        booking_required=False,
        tips="This activity was added in response to your revision request.",
    )


def _mark_note(day: DailyPlan, text: str) -> None:
    day.practical_notes = f"Updated per your request: \"{text[:120]}\""
    if not day.theme.startswith("✏️"):
        day.theme = "✏️ " + day.theme


_CHEAPER_ACCOMMODATION_OPTIONS = (
    "Budget-Friendly Guesthouse",
    "Cozy Backpacker Hostel",
    "Affordable City Inn",
    "Value Stay Lodge",
)
_BUDGET_REDUCTION_FACTOR = 0.7  # ~30% cheaper per reject; compounds on repeated rejects


def _apply_budget_scale(day: DailyPlan, scale: float) -> None:
    """Scale every activity AND the day's total by the same factor — unlike
    _recompute_day_cost, this does not re-add the flat transport/misc amount,
    so an explicit target budget (e.g. "under 900") is actually reachable."""
    for slot in _SLOTS:
        for activity in getattr(day, slot):
            activity.estimated_cost_per_person = round(activity.estimated_cost_per_person * scale, 2)
    day.estimated_daily_cost_per_person = round(day.estimated_daily_cost_per_person * scale, 2)


def apply_modification(
    daily_plans: list[DailyPlan],
    intent: ModificationIntent,
    destination: str,
    activity_pool: list[tuple] | None = None,
    num_travelers: int = 1,
    full_activity_pool: list[tuple] | None = None,
) -> list[DailyPlan]:
    """
    Returns a NEW list of DailyPlan with the requested change applied.

    Day/slot-targeted operations (replace/add/remove/swap/update_accommodation)
    mutate only that one day. Holistic operations (reduce_budget,
    regenerate_activities, adjust_activity_type) — the only kind Reject
    feedback ever produces, since RejectModal has no day dropdown — apply
    across every day (or the one named day, for adjust_activity_type).

    activity_pool: optional (name, description, cost, duration_hours, category)
    tuples the caller can supply so "I don't like these activities" can swap in
    genuinely different content instead of just leaving a note.

    full_activity_pool: the FULL catalogue across every category, used only for
    adjust_activity_type. activity_pool is filtered to the traveler's chosen
    interests, so if their interests are all outdoor there'd be no indoor
    candidates to swap in for "more indoor activities" without this.

    num_travelers: needed to translate an explicit target ("under 900") into a
    scale factor against the itinerary's grand total (per-person cost x travelers).
    """
    plans = [d.model_copy(deep=True) for d in daily_plans]
    num_days = len(plans)
    if num_days == 0:
        return plans

    if intent.operation == "reduce_budget":
        new_hotel = _CHEAPER_ACCOMMODATION_OPTIONS[len(intent.raw_text) % len(_CHEAPER_ACCOMMODATION_OPTIONS)]
        city = destination.split(",")[0].strip()

        if activity_pool:
            # A budget complaint should change WHAT'S in the plan, not just
            # relabel the same activities at a discount — swap the priciest
            # activities for genuinely cheaper catalogue alternatives.
            #
            # Cycle through the cheaper 60% of the whole pool (not just
            # whichever handful is strictly below each individual activity's
            # price) so the swap has real variety instead of converging on
            # the same one or two free items across every day and slot.
            sorted_pool = sorted(activity_pool, key=lambda t: t[2])
            tier_size = max(3, len(sorted_pool) * 6 // 10)
            cheap_tier = sorted_pool[:tier_size]
            cursor = 0
            for day in plans:
                for slot in _SLOTS:
                    new_items = []
                    for activity in getattr(day, slot):
                        name, desc, cost, hours, _cat = cheap_tier[cursor % len(cheap_tier)]
                        cursor += 1
                        if cost < activity.estimated_cost_per_person:
                            new_items.append(Activity(
                                name=f"{city} — {name}",
                                description=desc,
                                location=destination,
                                duration_minutes=int(hours * 60),
                                estimated_cost_per_person=cost,
                                booking_required=cost > 30,
                                tips="Swapped to a more budget-friendly option per your feedback.",
                            ))
                        else:
                            new_items.append(activity)  # already cheaper than this candidate
                    setattr(day, slot, new_items)
                day.accommodation = new_hotel
                _recompute_day_cost(day)
        else:
            # No catalogue available (e.g. unit tests) — scale directly to the
            # named target if one was given, otherwise a flat ~30% cut. Do NOT
            # apply the flat cut and then separately check the target — that
            # would cut cost even when the target is already above the current
            # total (reduce_budget must never raise cost, but also must never
            # cut further than asked when a specific target is named).
            if intent.target_budget:
                current_grand_total = round(
                    sum(d.estimated_daily_cost_per_person for d in plans) * max(num_travelers, 1), 2
                )
                scale = intent.target_budget / current_grand_total if current_grand_total > 0 else 1.0
                scale = max(0.05, min(scale, 1.0))
            else:
                scale = _BUDGET_REDUCTION_FACTOR
            for day in plans:
                _apply_budget_scale(day, scale)
                day.accommodation = new_hotel

        # Honor an explicit number the user named ("make it under 900") with
        # additional proportional scaling on top, if swapping wasn't enough.
        if intent.target_budget:
            current_grand_total = round(
                sum(d.estimated_daily_cost_per_person for d in plans) * max(num_travelers, 1), 2
            )
            if current_grand_total > intent.target_budget > 0:
                scale = max(0.05, intent.target_budget / current_grand_total)
                for day in plans:
                    _apply_budget_scale(day, scale)

        for day in plans:
            _mark_note(day, intent.raw_text)
        return plans

    if intent.operation == "adjust_activity_type":
        preference = intent.activity_preference or "outdoor"
        is_bucket = preference in ("indoor", "outdoor")
        affected_days = [plans[intent.target_day - 1]] if intent.target_day else plans
        lookup_pool = full_activity_pool or activity_pool

        if not lookup_pool:
            for day in affected_days:
                day.practical_notes = f"Noted your feedback: \"{intent.raw_text[:150]}\""
            return plans

        if is_bucket:
            want_outdoor = preference == "outdoor"
            candidates = [t for t in lookup_pool if CATEGORY_IS_OUTDOOR.get(t[4], False) == want_outdoor]
        else:
            candidates = [t for t in lookup_pool if t[4] == preference]
        if not candidates:
            candidates = list(lookup_pool)  # nothing of the requested type in the pool — best effort

        def _wrong_category(cat: str | None) -> bool:
            if cat is None:
                return False
            if is_bucket:
                return CATEGORY_IS_OUTDOOR.get(cat, False) != (preference == "outdoor")
            return cat != preference

        city = destination.split(",")[0].strip()
        cursor = sum(ord(c) for c in intent.raw_text) % max(len(candidates), 1)

        for day in affected_days:
            # Cap the swap to ONE activity per day. "I want more X" should
            # visibly tilt every day toward X, not erase every other activity
            # across the whole itinerary and leave a monotonous all-X plan —
            # that's what happened before this cap existed.
            swapped = False
            for slot in _SLOTS:
                if swapped:
                    break
                items = getattr(day, slot)
                for idx, activity in enumerate(items):
                    cat = _infer_category(activity.name, lookup_pool)
                    if _wrong_category(cat):
                        name, desc, cost, hours, _cat = candidates[cursor % len(candidates)]
                        cursor += 1
                        items[idx] = Activity(
                            name=f"{city} — {name}",
                            description=desc,
                            location=destination,
                            duration_minutes=int(hours * 60),
                            estimated_cost_per_person=cost,
                            booking_required=cost > 30,
                            tips=f"Swapped in to lean more into your {preference} preference per your feedback.",
                        )
                        swapped = True
                        break
            if swapped:
                _recompute_day_cost(day)
                _mark_note(day, intent.raw_text)
        return plans

    if intent.operation == "regenerate_activities":
        if not activity_pool:
            # No source pool supplied — record the feedback rather than
            # fabricating replacement activities out of nothing.
            for day in plans:
                day.practical_notes = f"Noted your feedback: \"{intent.raw_text[:150]}\""
            return plans
        city = destination.split(",")[0].strip()
        cursor = sum(ord(c) for c in intent.raw_text) % len(activity_pool)  # deterministic, feedback-dependent
        for day in plans:
            for slot in _SLOTS:
                name, desc, cost, hours, _cat = activity_pool[cursor % len(activity_pool)]
                cursor += 1
                setattr(day, slot, [Activity(
                    name=f"{city} — {name}",
                    description=desc,
                    location=destination,
                    duration_minutes=int(hours * 60),
                    estimated_cost_per_person=cost,
                    booking_required=cost > 30,
                    tips="Swapped in based on your feedback about the previous activities.",
                )])
            _recompute_day_cost(day)
            _mark_note(day, intent.raw_text)
        return plans

    if intent.operation == "swap" and intent.target_day and intent.swap_day2:
        day1 = plans[intent.target_day - 1]
        day2 = plans[intent.swap_day2 - 1]
        slot1, slot2 = intent.target_slot or "morning", intent.swap_slot2 or "morning"
        val1, val2 = getattr(day1, slot1), getattr(day2, slot2)
        setattr(day1, slot1, val2)
        setattr(day2, slot2, val1)
        _recompute_day_cost(day1)
        _recompute_day_cost(day2)
        _mark_note(day1, intent.raw_text)
        _mark_note(day2, intent.raw_text)
        return plans

    if intent.operation == "update_accommodation":
        # Reject (and Modify's "All Days" option) never name a day — a hotel
        # complaint with no day named means the whole trip's hotel, not
        # just Day 1's.
        affected_days = [plans[intent.target_day - 1]] if intent.target_day else plans
        new_acc = (intent.new_text or "").strip().title()
        for day in affected_days:
            day.accommodation = new_acc or day.accommodation
            _mark_note(day, intent.raw_text)
        return plans

    if intent.operation == "replace":
        # Reject's feedback box (and Modify's "All Days" option) has no day
        # picker — "replace scuba diving with jet skiing" gives no day at
        # all. Defaulting to Day 1 regardless of where the activity actually
        # is would silently do nothing on the day the user meant. Search
        # every day for the named activity first; only fall back to Day 1
        # when there's no name to search for (e.g. "replace it with X").
        day_idx = _resolve_target_day_index(intent, plans)
        day = plans[day_idx]
        slot = intent.target_slot or _find_slot_with_activity(day, intent.old_text or "") or "morning"
        new_activity = _new_activity(intent.new_text or "Custom Activity", destination, intent.raw_text)
        items = getattr(day, slot)
        replaced = False
        if intent.old_text:
            for idx, activity in enumerate(items):
                if _activity_matches(activity, intent.old_text):
                    items[idx] = new_activity
                    replaced = True
                    break
        if not replaced:
            # No specific old activity named (or no match) — the whole slot is what was targeted
            setattr(day, slot, [new_activity])
        _recompute_day_cost(day)
        _mark_note(day, intent.raw_text)
        return plans

    if intent.operation == "remove":
        day_idx = _resolve_target_day_index(intent, plans)
        day = plans[day_idx]
        slot = intent.target_slot or _find_slot_with_activity(day, intent.old_text or "")
        if slot is not None and intent.old_text:
            items = getattr(day, slot)
            setattr(day, slot, [a for a in items if not _activity_matches(a, intent.old_text)])
            _recompute_day_cost(day)
        _mark_note(day, intent.raw_text)
        return plans

    if intent.operation == "add":
        day = plans[max(0, min((intent.target_day or 1) - 1, num_days - 1))]
        slot = intent.target_slot or "evening"
        new_activity = _new_activity(intent.new_text or "Custom Activity", destination, intent.raw_text)
        getattr(day, slot).append(new_activity)
        _recompute_day_cost(day)
        _mark_note(day, intent.raw_text)
        return plans

    # No structural operation recognised — record the feedback without
    # inventing activities, so unrecognised requests never corrupt the plan.
    day = plans[max(0, min((intent.target_day or 1) - 1, num_days - 1))]
    day.practical_notes = f"Noted your feedback: \"{intent.raw_text[:150]}\""
    return plans
