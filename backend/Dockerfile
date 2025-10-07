# Stage 1: Define the base image
# Use a lean, Python-specific base image.
# 'slim-buster' is a good balance of size and required dependencies.
FROM python:3.11-slim-buster

# --- Environment Setup ---

# Set the working directory inside the container
WORKDIR /app

# --- Dependencies & Code ---

# Copy the requirements file into the container
# This step is often separated to leverage Docker's build cache
COPY requirements.txt .

# Install Python dependencies
# The --no-cache-dir flag helps keep the image size down
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# --- Execution Command ---

# Define the command to run when the container starts
# Use the executable form (CMD ["executable", "param1", "param2"])
# This should point to your main application file (e.g., your ML model entry point)
CMD ["python", "main.py"]


