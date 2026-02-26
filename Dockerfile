# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /usr/src/app

# Install dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /usr/src/app/wheels -r requirements.txt


# Stage 2: Runner
FROM python:3.11-slim

# Create a non-root user
RUN addgroup --system app && adduser --system --group app

# Set working directory
WORKDIR /home/app

# Copy installed dependencies from builder stage
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .

# Install dependencies from local wheels
RUN pip install --no-cache /wheels/*

# Copy application code
COPY ./app ./app

# Set permissions
RUN chown -R app:app /home/app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Run the application
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8080"]
