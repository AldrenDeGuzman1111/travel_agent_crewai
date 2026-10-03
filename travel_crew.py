"""CrewAI agents, tasks, and structured output for travel planning."""

from datetime import date
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task
from crewai_tools import SerperDevTool
from pydantic import BaseModel, Field


# TripRequest captures the input the user submits for a single trip.
# The rest of the workflow uses it to create a structured research brief and itinerary.
class TripRequest(BaseModel):
    destination: str
    trip_length_days: int
    interests: list[str]
    start_date: str | None = None
    end_date: str | None = None
    travelers: int = 1
    budget_level: str | None = None
    currency: str = "USD"
    preferences: str | None = None


# ResearchSource stores each web result used by the research agent so the final
# itinerary can show where it came from.
class ResearchSource(BaseModel):
    title: str = Field(description="Title of the web source")
    url: str = Field(description="Direct source URL")
    note: str = Field(description="What this source contributed to the plan")


# The research agent produces a structured brief based on current destination data.
class TravelResearch(BaseModel):
    destination_summary: str
    activity_findings: list[str]
    practical_considerations: list[str]
    budget_signals: list[str]
    sources: list[ResearchSource] = Field(default_factory=list)


# DailyActivity describes one item in the day-by-day plan with timing,
# purpose, budget estimate, and practical notes.
class DailyActivity(BaseModel):
    time_of_day: str
    activity: str
    description: str
    area: str
    estimated_cost: str
    practical_note: str | None = None


# ItineraryDay groups the activities for one travel day and keeps the overall day
# spend and transport guidance together.
class ItineraryDay(BaseModel):
    day_number: int
    theme: str
    activities: list[DailyActivity]
    transport_note: str
    estimated_daily_cost: str


class BudgetLineItem(BaseModel):
    category: str
    estimated_amount: str
    assumptions: str


class TravelPlan(BaseModel):
    destination: str
    trip_length_days: int
    trip_overview: str
    travel_style: str
    daily_itinerary: list[ItineraryDay]
    budget_total_estimate: str
    budget_outline: list[BudgetLineItem]
    travel_considerations: list[str]
    booking_checklist: list[str]
    sources: list[ResearchSource] = Field(default_factory=list)
    responsible_travel_note: str


# Validate the form inputs before sending them to the LLM so the app catches
# missing or contradictory trip details early.
def validate_trip_request(
    destination: str,
    trip_length_days: int,
    interests: list[str],
    start_date: date | None,
    end_date: date | None,
) -> list[str]:
    """Return user-facing validation messages before an API call is made."""
    errors = []
    if not destination.strip():
        errors.append("Enter a destination.")
    if not 1 <= trip_length_days <= 21:
        errors.append("Trip length must be between 1 and 21 days.")
    if not [interest for interest in interests if interest.strip()]:
        errors.append("Select at least one interest or add a custom interest.")
    if (start_date is None) != (end_date is None):
        errors.append("Provide both a start date and an end date.")
    if start_date and end_date and end_date < start_date:
        errors.append("The end date must be on or after the start date.")
    return errors


# Build the CrewAI workflow: the researcher gathers live destination data while
# the planner turns that research into a day-by-day itinerary and budget.
def build_travel_crew(model_name: str, use_live_research: bool) -> Crew:
    """Build a sequential research-and-planning Crew using environment credentials."""
    llm = LLM(model=f"openai/{model_name}", temperature=0.2)
    research_tools = [SerperDevTool()] if use_live_research else []
    research_instruction = (
        "Use web search for current attractions, logistics, seasonal issues, and indicative costs. "
        "Include only sources you actually consulted."
        if use_live_research
        else "Do not use or claim to have used live web sources. Base the brief on general travel knowledge, "
        "keep sources empty, and make time-sensitive details explicit items for the traveler to verify."
    )

    researcher = Agent(
        role="Travel Researcher",
        goal="Find current, credible information needed to plan an enjoyable and practical trip.",
        backstory=(
            "You are a meticulous destination researcher who verifies attractions, transport, "
            "seasonal details, and indicative local costs through current web sources."
        ),
        tools=research_tools,
        llm=llm,
        verbose=True,
    )
    planner = Agent(
        role="Travel Itinerary Planner",
        goal="Create realistic, well-paced, personalized travel itineraries with transparent budget assumptions.",
        backstory=(
            "You are an experienced trip designer. You cluster nearby activities, avoid overpacked "
            "days, and distinguish estimates from facts requiring traveler confirmation."
        ),
        llm=llm,
        verbose=True,
    )

    research_task = Task(
        description=(
            "Research {destination} for a {trip_length_days}-day trip. The traveler is interested in "
            "{interests}; travel dates are {travel_dates}; there are {travelers} traveler(s); budget "
            "level is {budget_level}; preferred currency is {currency}; additional preferences are "
            "{preferences}. "
            f"{research_instruction} Do not claim prices, hours, "
            "visa requirements, or availability are guaranteed."
        ),
        expected_output="A structured destination research brief with findings, practical considerations, budget signals, and source URLs.",
        agent=researcher,
        output_pydantic=TravelResearch,
    )
    itinerary_task = Task(
        description=(
            "Using the travel research brief, create a {trip_length_days}-day plan for {destination}. "
            "Honor interests ({interests}), dates ({travel_dates}), traveler count ({travelers}), budget "
            "level ({budget_level}), currency ({currency}), and preferences ({preferences}). Create exactly "
            "{trip_length_days} itinerary days. Group nearby activities, allow reasonable transit and rest, "
            "and use clear estimated amounts rather than invented precision. Reuse only sources provided in "
            "the research brief; return an empty source list when none are available. Include a note telling "
            "the traveler to verify time-sensitive details."
        ),
        expected_output="A validated TravelPlan JSON report with daily activities, travel considerations, budget outline, checklist, and sources.",
        agent=planner,
        context=[research_task],
        output_pydantic=TravelPlan,
    )
    return Crew(
        agents=[researcher, planner],
        tasks=[research_task, itinerary_task],
        process=Process.sequential,
        verbose=True,
    )


# Execute the assembled crew with the user's trip request and validate the
# final result before rendering it in Streamlit.
def run_travel_crew(crew: Crew, request: TripRequest) -> tuple[TravelPlan, Any]:
    """Execute a Crew and ensure its final response matches the UI's report model."""
    inputs = request.model_dump()
    inputs["interests"] = ", ".join(request.interests)
    inputs["travel_dates"] = (
        f"{request.start_date} to {request.end_date}" if request.start_date and request.end_date else "flexible dates"
    )
    inputs["budget_level"] = request.budget_level or "not specified"
    inputs["preferences"] = request.preferences or "none provided"
    result = crew.kickoff(inputs=inputs)
    if result.pydantic is None:
        raise ValueError("The crew returned an unstructured result. Please try again.")
    plan = result.pydantic if isinstance(result.pydantic, TravelPlan) else TravelPlan.model_validate(result.pydantic)
    if len(plan.daily_itinerary) != request.trip_length_days:
        raise ValueError("The crew did not create an itinerary for every requested day. Please try again.")
    return plan, result
