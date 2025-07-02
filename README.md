# fastmcplangcalcbot
This is a basic greeting and calculator MCP service, therefore by accessing the routes: /greeting will be given back a greeting; /sum_two_numbers will perform and respond with a basic sum ; /mcp will expose both previous routes

# Running the project
Apply the commands
docker build -t fastapi-mcp
docker docker run -p 8000:8000 fastapi-mcp

# Alternatively build the Virtual Environment
At the project´s folder, apply the command python -m venv venv then activate it by applying the commnad source venv/bin/activate , make all install using pip then turn on the server by applying te command uvicorn app.main:app --reload