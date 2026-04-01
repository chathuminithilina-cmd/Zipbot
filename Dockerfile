# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Create the storage directory
RUN mkdir -p user_files

# Start the bot
CMD ["python", "bot.py"]
