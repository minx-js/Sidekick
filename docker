FROM python:3.12-slim

# Node.js (needed for the two MCP servers that start with npx)
RUN apt-get update && apt-get install -y curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Playwright MCP server + the Chromium browser it uses
RUN npm install -g @playwright/mcp \
    && cd "$(npm root -g)/@playwright/mcp" \
    && npx playwright install --with-deps chromium

# Filesystem MCP server
RUN npm install -g @modelcontextprotocol/server-filesystem

WORKDIR /app
RUN pip install --no-cache-dir uv
COPY . .
RUN uv sync

CMD ["uv", "run", "app.py"]
