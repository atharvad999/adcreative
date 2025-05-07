from dotenv import load_dotenv
import os

load_dotenv()

SHUTTERSTOCK_API_KEY = os.getenv("SHUTTERSTOCK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID")