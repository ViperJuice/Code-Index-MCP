import os


def connect():
    api_key = os.getenv("API_KEY")
    return f"Connected with {api_key}"
