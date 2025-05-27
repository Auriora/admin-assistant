from web.app import create_app
import os
from dotenv import load_dotenv

# Determine which .env file to load based on APP_ENV
env = os.environ.get('APP_ENV', 'development').lower()
dotenv_file = f'.env.{env}'
if os.path.exists(dotenv_file):
    load_dotenv(dotenv_file)
else:
    # Fallback to .env if specific file not found
    if os.path.exists('.env'):
        load_dotenv('.env')

web_app = create_app()

if __name__ == "__main__":
    web_app.run() 