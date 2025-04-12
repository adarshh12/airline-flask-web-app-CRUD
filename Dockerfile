# Use the official Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy all files and folders from the project directory to the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the Flask application's port (default 5000)
EXPOSE 5000

# Set the default command to run the app
CMD ["python", "app.py"]
