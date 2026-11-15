FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "fastmcp>=4.2.0" "httpx>=0.27"

COPY cronometer_mcp_server.py auth.py ./

# Railway (and most PaaS targets) inject PORT at runtime; the server reads
# it directly, so EXPOSE here is documentation, not a binding default.
EXPOSE 8000

CMD ["python", "cronometer_mcp_server.py"]
