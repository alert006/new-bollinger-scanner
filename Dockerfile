# Use the official Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Streamlit app script
COPY app.py .

# Set the entry point to run the Streamlit app on the correct port
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.enableCORS=true", "--server.enableXsrfProtection=true"]

# Expose the port Streamlit uses
EXPOSE 8501
