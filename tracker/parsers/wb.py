import requests
from bs4 import BeautifulSoup
import json
def parse_wildberries(url):
    headers = {
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/437.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Делаю первым способом через JSON-LD
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if 'offers' in data:
                    price = float(data['offers']['price'])
                    name = data.get('name', 'Товар WB')
                    return price, name
            except:
                continue

            return None, None
    except Exception as e:
        print(f"Error parsing WB: {e}")
        return None, None

    return None, None

