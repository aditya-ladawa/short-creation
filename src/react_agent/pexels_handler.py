from pexels_apis import PexelsAPI
import os
from dotenv import load_dotenv

load_dotenv()

pexels = PexelsAPI(os.environ.get('PEXELS_API_KEY'))