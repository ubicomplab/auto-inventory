# Dockerfile

FROM python:3.11-slim

# Set work directory inside the container
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

# Make Python output unbuffered (logs show up immediately)
ENV PYTHONUNBUFFERED=1

# Default command: run the pipeline once
CMD ["python", "-m", "src.main"]

