# Use an official Python runtime as a parent image
FROM python:3.8-slim-buster

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Set the working directory in the container to /app
WORKDIR /app

# Add current directory files to /app in container
ADD . /app

# Upgrade pip and install only the necessary Python packages
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir flask requests gunicorn

# Expose the port Flask will run on
EXPOSE 5000

# Run the Flask app with Gunicorn when the container launches
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
