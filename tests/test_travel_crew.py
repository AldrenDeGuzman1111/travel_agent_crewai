from datetime import date

from travel_crew import TravelResearch, TripRequest, TravelPlan, validate_trip_request


def test_validate_trip_request_accepts_complete_request():
    errors = validate_trip_request(
        "Kyoto, Japan",
        4,
        ["Culture & history"],
        date(2026, 4, 10),
        date(2026, 4, 13),
    )

    assert errors == []


def test_validate_trip_request_reports_missing_required_values():
    errors = validate_trip_request("", 0, [], None, None)

    assert "Enter a destination." in errors
    assert "Trip length must be between 1 and 21 days." in errors
    assert "Select at least one interest or add a custom interest." in errors


def test_validate_trip_request_rejects_reversed_dates():
    errors = validate_trip_request(
        "Lisbon, Portugal",
        3,
        ["Food & local markets"],
        date(2026, 6, 10),
        date(2026, 6, 8),
    )

    assert errors == ["The end date must be on or after the start date."]


def test_trip_request_serializes_cleanly_for_crew_inputs():
    request = TripRequest(destination="Reykjavik, Iceland", trip_length_days=3, interests=["Nature & outdoors"])

    assert request.model_dump()["destination"] == "Reykjavik, Iceland"
    assert TravelPlan.model_fields["daily_itinerary"].is_required()


def test_research_sources_can_be_empty_without_live_web_research():
    research = TravelResearch(
        destination_summary="A compact city break.",
        activity_findings=["Visit museums."],
        practical_considerations=["Verify opening times."],
        budget_signals=["Costs vary by season."],
    )

    assert research.sources == []
