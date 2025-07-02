from fastapi import FastAPI, HTTPException
from fastapi_mcp import FastApiMCP
from pydantic import BaseModel, ValidationError
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import pandas as pd
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import json

app = FastAPI(title="FastAPI Server", version="0.1.0")
load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GreetingInput(BaseModel):
    name: str

class NumbersInput(BaseModel):
    number: int

class InteractionInput(BaseModel):
    text: str

@app.get("/")
async def read_root():
    """Returns a simple welcome message."""
    return {"message": "Welcome to the FastAPI Server!"}

@app.get("/greet/{name}", operation_id='greet_user')
async def greet_user(name_input: GreetingInput):
    """Greets the user by name."""
    return {"message": f"Hello, {name_input.name}!"}

@app.post("/add", operation_id="add_two_numbers")
async def add_two_numbers(a: NumbersInput, b: NumbersInput):
    """Add two numbers and return the sum."""
    number_1 = a.number
    number_2 = b.number
    sum_result = pd.DataFrame({"a": [number_1], "b": [number_2], "sum": [number_1 + number_2]})
    result = int(sum_result.loc[0, "sum"])
    return {"result": result}

@app.post("/subtract", operation_id="subtract_two_numbers")
async def subtract_two_numbers(a: NumbersInput, b: NumbersInput):
    """Subtract two numbers and return the result."""
    try:
        result = int(a.number - b.number)
        return {"result": result}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(ve))

@app.post('/multiply', operation_id="multiply_two_numbers")
async def multiply_two_numbers(a: NumbersInput, b: NumbersInput):
    """Multiply two numbers and return the result."""
    try:
        result = int(a.number * b.number)
        return {"result": result}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post('/divide', operation_id="divide_two_numbers")
async def divide_two_numbers(a: NumbersInput, b: NumbersInput):
    """Divide two numbers and return the result."""
    try:
        result = int(a.number / b.number)
        return {"result": result}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post('/ask', operation_id="ask")
async def ask(interaction: InteractionInput):
    """Expose a MCP capable server to make math as a calculator."""
    mcp_config = {
        "calculator": {  # Give our server a name within the client config
            "url": "http://127.0.0.1:8000/mcp",  # URL of our running FastAPI MCP server
            "transport": "sse",  # Use HTTP + SSE transport
        }
    }
    llm = ChatOpenAI(model="gpt-4o")
    print("Connecting to MCP server(s)...")
    client = MultiServerMCPClient(mcp_config)
    print("Discovering tools...")
    tools = await client.get_tools()  # This fetches tools from all configured servers

    if not tools:
        print("Error: No tools discovered from the MCP server.")
        print("Ensure the server is running and fastapi-mcp is mounted AFTER route definitions.")
        return

    print(f"Discovered tools: {[tool.name for tool in tools]}")

    # Create the LangGraph ReAct Agent
    agent_executor = create_react_agent(llm, tools)
    print("Agent created. Ready for query.")

    # --- Test Queries ---
    # Query 1: Should use the read_root tool
    query1 = interaction.text
    print(f"\nInvoking agent with query: '{query1}' ?")
    final_answer_q1 = ""
    all_events_q1 = []  # List to collect events for query 1
    async for event in agent_executor.astream_events({"messages": [("user", query1)]}, version="v1"):
        # Only process/collect events that are NOT chat model streams
        if event["event"] != "on_chat_model_stream":
            # Create a simplified version of the event for logging
            simplified_event = {
                "event_type": event["event"],
                "name": event.get("name", "Unknown")  # Get name, provide default
            }

            if event["event"] == "on_tool_start":
                simplified_event["input"] = event.get("data", {}).get("input")
            elif event["event"] == "on_tool_end":
                output_data = event.get("data", {}).get("output")
                try:
                    # Try to parse if it's a JSON string
                    if isinstance(output_data, str):
                        simplified_event["output"] = json.loads(output_data)
                    else:
                        simplified_event["output"] = output_data  # Keep as is if not string
                except (json.JSONDecodeError, TypeError):
                    # Fallback for non-JSON strings or other types
                    simplified_event["output(raw)"] = output_data

            all_events_q1.append(simplified_event)  # Collect the simplified event

        kind = event["event"]
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                # print(content, end="|") # Commented out to reduce noise
                final_answer_q1 += content  # Still accumulate final answer
        elif kind == "on_tool_start":
            print("\n-- TOOL START --")
            print(f"Tool Name: {event['name']}")
            print(f"Tool Args: {json.dumps(event['data'].get('input'), indent=2)}")  # Pretty print args
        elif kind == "on_tool_end":
            print("\n-- TOOL END --")
            print(f"Tool Name: {event['name']}")
            try:
                # Handle potential non-string output before loading
                output_data = event['data'].get('output')
                if isinstance(output_data, str):
                    tool_output = json.loads(output_data)
                    print(f"Tool Output:\n{json.dumps(tool_output, indent=2)}")
                else:
                    # If output isn't a string, print its representation
                    print(f"Tool Output (non-string): {output_data}")
            except (json.JSONDecodeError, TypeError):
                # Fallback for non-JSON string output
                print(f"Tool Output (raw string): {event['data'].get('output')}")
            print("----------------")

    # ---- Print results AFTER the loop for Query 1 ----
    print("\n-- AGENT FINISHED Q1 --")
    print(f"Final Answer: {final_answer_q1}")
    print("\n-- Collected Events for Q1 --")
    try:
        print(json.dumps(all_events_q1, indent=2, default=str))
    except Exception as e:
        print(f"Could not serialize events: {e}")
    print("=======================\n")
    return {"result": final_answer_q1}
    # ---- End printing results for Query 1 ----

mcp = FastApiMCP(app, name="MCP Service", include_operations=["ask", "add_two_numbers", "divide_two_numbers", "greet_user", "multiply_two_numbers", "subtract_two_numbers"])
mcp.mount()
