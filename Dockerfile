FROM python:3.8.20-slim-bullseye
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
RUN apt update && apt install -y curl && \
    adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app 
    

USER appuser
EXPOSE 5000

CMD ["python", "src/app.py"]