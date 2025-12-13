import os
from dotenv import load_dotenv
from shodan import Shodan

# Load environment variables from .env file
load_dotenv()

SHODAN_API_KEY = os.getenv('SHODAN_API_KEY')

if not SHODAN_API_KEY:
    raise ValueError("SHODAN_API_KEY not found in environment variables. Please check your .env file.")

api = Shodan(SHODAN_API_KEY)

MY_IP = os.getenv('MY_PUBLIC_IP')

# Lookup an IP
if MY_IP:
    print(f"Looking up IP: {MY_IP}")
    try:
        ipinfo = api.host(MY_IP)
        print(ipinfo)
    except Exception as e:
        print(f"Error looking up {MY_IP}: {e}")
else:
    print("MY_PUBLIC_IP not set in .env")

# Search for websites that have been "hacked"
for banner in api.search_cursor('http.title:"hacked by"'):
    print(banner)

# Get the total number of industrial control systems services on the Internet
ics_services = api.count('tag:ics')
print('Industrial Control Systems: {}'.format(ics_services['total']))