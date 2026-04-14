FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    conntrack \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

COPY agent.py /app/agent.py

ENV NODE_KICK_PORT=62010
ENV NODE_KICK_TOKEN=""

CMD ["python", "agent.py"]
