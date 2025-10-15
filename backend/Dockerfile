# backend/Dockerfile

# 1. Start with a lean, official Python base image.
FROM python:3.11-slim

# 2. Set the working directory inside the container.
WORKDIR /app

# 3. Copy only the requirements file first to leverage Docker's build cache.
#    This layer only rebuilds when your dependencies change.
COPY ./requirements.txt .

# 4. Install dependencies. We include build-essentials in case any libraries
#    need to compile C extensions (like psycopg2), then clean up to keep the image small.
RUN apt-get update && apt-get install -y build-essential libpq-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove build-essential

# 5. Copy the rest of your application source code into the container.
COPY . .

# 6. Expose the port that the application will listen on.
#    Cloud Run expects 8080 by default.
EXPOSE 8080

# 7. Define the command to run your application.
#    Listen on 0.0.0.0 to accept connections from outside the container.
#    The port is dynamically set by the $PORT environment variable, which Cloud Run provides.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
