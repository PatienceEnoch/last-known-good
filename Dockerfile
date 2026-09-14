FROM python:3.12-slim

RUN apt-get update \
    && apt-get install --no-install-recommends -y iproute2 iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir .

CMD ["sleep", "infinity"]
