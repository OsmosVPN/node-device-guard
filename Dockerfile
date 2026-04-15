FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

COPY agent.py /app/agent.py

ENV NODE_KICK_PORT=62010
ENV NODE_KICK_TOKEN=""

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os,urllib.request; port=os.getenv('NODE_KICK_PORT','62010'); urllib.request.urlopen('http://127.0.0.1:%s/health' % port, timeout=3).read()" || exit 1

CMD ["python", "agent.py"]
