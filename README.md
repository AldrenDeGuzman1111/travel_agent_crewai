# Travel Planning Agent

A Streamlit proof of concept that creates a researched, structured travel itinerary. A user supplies a destination, trip length, interests, and optional dates, travelers, budget, and constraints. The application searches the web for current destination information, then produces daily activities, travel considerations, a budget outline, and source links.

## Features

- Streamlit trip request form with suggested interests and optional trip details
- Two collaborating CrewAI agents: a live-web Travel Researcher and an Itinerary Planner
- Serper web search for timely attractions, logistics, and indicative cost research, controlled by an enabled-by-default form checkbox
- OpenAI LLM configured only through environment variables
- Pydantic-validated JSON output rendered as a readable Streamlit report
- Visible CrewAI execution result for demos
- Input validation, clear API/configuration errors, logging, and cached Crew configuration

## Architecture

```text
Streamlit form
    -> Travel Researcher Agent + Serper search tool (when live research is enabled)
    -> research_task output (TravelResearch)
    -> Itinerary Planner Agent
    -> itinerary_task output (TravelPlan Pydantic JSON)
    -> Streamlit itinerary report
```

### How Agent, Task, and Crew work together

- An **Agent** has a role, goal, backstory, available tools, and an LLM. When the enabled-by-default **Use live travel research** checkbox is selected, the `Travel Researcher` uses Serper to find timely information. When it is cleared, the researcher creates a clearly caveated plan without claiming live sources. The `Travel Itinerary Planner` converts the research into a practical trip.
- A **Task** is a specific deliverable assigned to an Agent. `research_task` produces a structured research brief. `itinerary_task` receives that brief as context and returns the final `TravelPlan` Pydantic model.
- A **Crew** groups both agents and tasks. It runs them sequentially: research first, itinerary planning second. The Streamlit app starts the Crew with the form data and renders its structured final result.

## Setup

Use Python 3.10 through 3.13. The CrewAI dependency does not currently support Python 3.14.

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Set the required API keys for the current PowerShell session:

   ```powershell
   $env:OPENAI_API_KEY = "your-openai-key"
    $env:SERPER_API_KEY = "your-serper-key"
   ```

    Alternatively, copy `.env.example` to `.env` and set the same values. The app loads `.env` locally. Streamlit secrets are also supported. `SERPER_API_KEY` is required only when live travel research is enabled.

4. Optional: select a different OpenAI model:

   ```powershell
   $env:OPENAI_MODEL = "gpt-4o-mini"
   ```

5. Run the application:

   ```powershell
   streamlit run app.py
   ```

## Testing

```powershell
python -m pytest
```

## Responsible Use

The budget is an estimate, not a quote. Search results, prices, opening hours, visa requirements, weather, safety conditions, and availability can change. Verify important details with official providers before booking or traveling.
