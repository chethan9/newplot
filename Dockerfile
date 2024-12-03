# Use an official Python runtime as a parent image
FROM python:3.8-slim-buster

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Set the working directory in the container to /app
WORKDIR /app

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \
    liblapack-dev && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and install necessary Python packages
RUN python3 -m pip install --upgrade pip setuptools wheel

# Add current directory files to /app in container
ADD . /app

# Install only the necessary Python packages for the endpoint
RUN pip install --no-cache-dir \
    flask \
    requests \
    pandas \
    gunicorn

# Expose the port Flask will run on
EXPOSE 5000

# Run the Flask app with Gunicorn when the container launches
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
