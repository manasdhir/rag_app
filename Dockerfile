# Use a lightweight official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy all project files into the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Set environment variables directly here (⚠️ Not safe for production)
ENV PINECONE_API_KEY=pcsk_ueZNX_216ZdxhgjYznLYCg87a1PLWVVhbefmnKvH1iPt2ic5Z5twzk14Kia2rbVjoSPSc
ENV PINECONE_INDEX_NAME=ragdocs
ENV GEMINI=AIzaSyDt6ottoOurSbY_WhW0K9_nz-PW9mNrlSQ

# Expose Flask port
EXPOSE 5000

# Default command to run the app
CMD ["python", "app.py"]
