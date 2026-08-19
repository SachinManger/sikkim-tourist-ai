from agent.tourist_agent import (
    asks_for_current_road_condition,
    answer_guide_for_intent,
    append_missing_snt_option,
    available_transport_modes,
    build_exact_fare_answer,
    build_route_context,
    classify_intent,
    extract_requested_route,
    generate_suggested_followups,
    record_contains_route,
    requested_transport_mode,
)


def test_taxi_fare_question_routes_to_transport():
    assert classify_intent("What is the taxi fare from NJP to Gangtok?") == "transport"


def test_road_condition_question_routes_to_transport():
    assert classify_intent("How is the road from Gangtok to Darjeeling?") == "transport"
    assert asks_for_current_road_condition("How is the road from Gangtok to Darjeeling?")


def test_transport_followups_stay_on_transport_topic():
    followups = generate_suggested_followups("transport", "taxi fare")
    combined = " ".join(followups).lower()

    assert "food" not in combined
    assert "cuisine" not in combined
    assert "taxi" in combined or "journey" in combined


def test_snt_bus_fare_record_is_ranked_first():
    from retrieval.search import search_approved_records

    results = search_approved_records(
        "fare from Namchi to Siliguri on SNT bus",
        category="transport",
        limit=5,
    )

    assert results
    assert results[0]["record"]["name"] == "SNT Bus Schedule and Fares"
    assert all("Taxi Rate Chart" != item["record"]["name"] for item in results)


def test_transport_mode_scope_follows_the_question():
    assert requested_transport_mode("fare from Namchi to Siliguri") == "all"
    assert requested_transport_mode("SNT fare from Namchi to Siliguri") == "bus"
    assert requested_transport_mode("reserved taxi fare from Namchi to Siliguri") == "taxi"


def test_exact_route_filter_rejects_unrelated_route_mentions():
    route = extract_requested_route("fare from Namchi to Siliguri on SNT bus")
    assert route == ("namchi", "siliguri")
    assert record_contains_route(
        {"price_range": "Namchi → Siliguri: ₹220"},
        *route,
    )
    assert not record_contains_route(
        {"price_range": "Gangtok → Namchi: ₹4,000; Gangtok → Siliguri: ₹4,000"},
        *route,
    )

    assert extract_requested_route(
        "How can I reach Gangtok from Siliguri?"
    ) == ("siliguri", "gangtok")


def test_exact_fare_answer_preserves_mode_and_price_conditions():
    results = [
        {
            "record": {
                "name": "SNT Bus Schedule and Fares",
                "aliases": ["Namchi to Siliguri SNT Bus"],
                "category": "transport",
                "price_range": "Namchi → Siliguri: ₹220",
            }
        },
        {
            "record": {
                "name": "Namchi to Siliguri Reserved Taxi Fare",
                "aliases": ["Namchi to Siliguri cab fare"],
                "category": "taxi",
                "price_range": "Namchi → Siliguri: starts at ₹4,036 one way",
                "dynamic_information": True,
            }
        },
    ]

    answer = build_exact_fare_answer(results, "namchi", "siliguri", "all")
    assert "₹220" in answer
    assert "₹4,036" in answer
    assert "extra charges may apply" in answer
    assert not answer.startswith("-")


def test_route_context_contains_only_en_route_logistics():
    result = {
        "record": {
            "name": "Namchi to Siliguri Route Guide",
            "aliases": ["Namchi to Siliguri travel"],
            "distance": "about 92 km",
            "duration": "Allow roughly 3–4 hours.",
            "how_to_reach": "Namchi → Melli → Sevoke → Siliguri.",
            "permit_information": "No special protected-area permit is required for Indian travelers.",
            "nearby_places": ["Melli", "Teesta River corridor", "Sevoke"],
        }
    }

    context = build_route_context([result], "namchi", "siliguri")
    assert "92 km" in context
    assert "Melli" in context
    assert "Permit" in context
    assert "Chardham" not in context


def test_each_intent_has_a_topic_specific_answer_guide():
    transport = answer_guide_for_intent("transport").lower()
    food = answer_guide_for_intent("food").lower()
    permit_guide = answer_guide_for_intent("permit").lower()

    assert "fare" in transport
    assert "ingredient" in food
    assert "documents" in permit_guide
    assert transport != food != permit_guide


def test_history_questions_do_not_route_to_destination_advice():
    assert classify_intent("Tell me the history of Sikkim") == "history"
    guide = answer_guide_for_intent("history").lower()
    assert "chronology" in guide
    assert "do not add best time" in guide


def test_available_snt_mode_is_never_omitted():
    results = [
        {
            "record": {
                "name": "Siliguri to Gangtok SNT Bus Schedule and Fares",
                "price_range": "Siliguri → Gangtok SNT normal bus: ₹275; Siliguri → Gangtok SNT A/C bus: ₹500",
                "schedule": ["Normal: 8:00 AM", "A/C: 10:30 AM"],
            }
        }
    ]

    assert "SNT bus" in available_transport_modes(results)
    answer = append_missing_snt_option("You can take a shared taxi.", results)
    assert "SNT bus service is also available" in answer
    assert "₹275" in answer
