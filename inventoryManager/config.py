import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration - load from environment variables
CLIENT_ID = os.getenv("JOBBER_DEV_CENTER_CLIENT_ID")
CLIENT_SECRET = os.getenv("JOBBER_DEV_CENTER_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("JOBBERS_REFRESH_TOKEN")
API_VERSION = os.getenv("JOBBER_API_VERSION", "2023-08-18") 

