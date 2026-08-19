FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Adjust -w (workers) to roughly (2 x CPU cores) + 1 as a starting point.
# Each worker loads its own copy of both models at startup via the
# lifespan handler in app.py.
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
