FROM python:3.11

WORKDIR /app

# Install system dependencies (including mediainfo)
RUN apt-get update && apt-get install -y \
    mediainfo \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python", "-m", "FileStream"]
