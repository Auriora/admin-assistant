import os

from dotenv import load_dotenv

from web.app import create_app

# Load environment variables from .env file only
if os.path.exists(".env"):
    load_dotenv(".env")

web_app = create_app()

if __name__ == "__main__":
    web_app.run()
