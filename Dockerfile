# Use an official Python runtime as a parent image
FROM python:3.8-slim-buster

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Set the working directory in the container to /app
WORKDIR /app

# Install basic dependencies and debug to check for errors
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \
    liblapack-dev \
    ffmpeg \
    firefox-esr \
    wget \
    curl \
    unzip \
    gnupg2 \
    ca-certificates && \
    apt-get clean

# Add Google Chrome installation
RUN echo "Attempting to install Google Chrome" && \
    curl -sSL https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    DISTRO=$(lsb_release -c | awk '{print $2}') && \
    echo "deb [signed-by=/usr/share/keyrings/google-linux-signing-key.pub] https://dl.google.com/linux/chrome/deb/ $DISTRO main" | tee /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    echo "Google Chrome installation complete"

# Install geckodriver
RUN echo "Attempting to install geckodriver" && \
    wget https://github.com/mozilla/geckodriver/releases/download/v0.29.1/geckodriver-v0.29.1-linux64.tar.gz -P /var/lib/data && \
    tar -xvzf /var/lib/data/geckodriver-v0.29.1-linux64.tar.gz -C /var/lib/data && \
    rm /var/lib/data/geckodriver-v0.29.1-linux64.tar.gz && \
    chmod +x /var/lib/data/geckodriver && \
    ln -s /var/lib/data/geckodriver /usr/local/bin/geckodriver && \
    echo "Geckodriver installation complete"

# Upgrade pip and install necessary Python packages
RUN python3 -m pip install --upgrade pip setuptools wheel

# Add current directory files to /app in container
ADD . /app

# Install necessary Python packages for the endpoint
RUN pip install --no-cache-dir \
    flask \
    requests \
    pandas \
    gunicorn \
    selenium \
    beautifulsoup4

# Expose the port Flask will run on
EXPOSE 5000

# Run the Flask app with Gunicorn when the container launches
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
