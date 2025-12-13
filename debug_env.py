import os
from dotenv import load_dotenv

load_dotenv()
print("CENSYS_TOKEN:", os.getenv('CENSYS_TOKEN'))
print("MY_PUBLIC_IP:", os.getenv('MY_PUBLIC_IP'))
