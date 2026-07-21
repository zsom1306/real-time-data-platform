import os

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

if not api_key:
    raise ValueError("ALPHA_VANTAGE_API_KEY was not found")

print("API key loaded successfully")