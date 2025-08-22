# Use the official Playwright Python image as the base image
FROM mcr.microsoft.com/playwright/python:v1.54.0-jammy

# Set the working directory in the container
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else including auth_state.json
COPY . .

# Ensure the auth_state.json file has appropriate permissions
RUN chmod 644 /app/auth_state.json

# Expose the port FastAPI will run on
EXPOSE 10000

# Run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
