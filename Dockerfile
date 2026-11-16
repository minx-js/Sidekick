FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @playwright/mcp \
    && cd "$(npm root -g)/@playwright/mcp" \
    && npx playwright install --with-deps chromium

RUN npm install -g @modelcontextprotocol/server-filesystem

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "app.py"]
