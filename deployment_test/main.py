# backend/main.py
from fastapi import FastAPI
import os

# Create the FastAPI application instance
app = FastAPI()

# Define a root endpoint for health checks
@app.get("/")
def read_root():
    """
    Root endpoint to confirm the API is running.
    """
    return {"status": "API is running"}

# A simple endpoint to check an environment variable
@app.get("/db-check")
def db_check():
    """
    Checks if database environment variables are set.
    This is a good way to confirm your docker-compose.yml is working.
    """
    db_host = os.getenv("DB_HOST", "not_set")
    return {"db_host": db_host}
