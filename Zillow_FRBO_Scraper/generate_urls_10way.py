import json
import urllib.parse
import copy

original_url = "https://www.zillow.com/chicago-il/rentals/?searchQueryState=%7B%22isMapVisible%22%3Atrue%2C%22mapBounds%22%3A%7B%22north%22%3A42.13769363060134%2C%22south%22%3A41.52888309438494%2C%22east%22%3A-87.19223863085938%2C%22west%22%3A-88.27164536914063%7D%2C%22filterState%22%3A%7B%22sort%22%3A%7B%22value%22%3A%22paymenta%22%7D%2C%22price%22%3A%7B%22min%22%3Anull%2C%22max%22%3A300000%7D%2C%22mp%22%3A%7B%22min%22%3Anull%7D%2C%22fr%22%3A%7B%22value%22%3Atrue%7D%2C%22fsba%22%3A%7B%22value%22%3Afalse%7D%2C%22fsbo%22%3A%7B%22value%22%3Afalse%7D%2C%22nc%22%3A%7B%22value%22%3Afalse%7D%2C%22cmsn%22%3A%7B%22value%22%3Afalse%7D%2C%22auc%22%3A%7B%22value%22%3Afalse%7D%2C%22fore%22%3A%7B%22value%22%3Afalse%7D%2C%22att%22%3A%7B%22value%22%3A%22by%20owner%22%7D%7D%2C%22isListVisible%22%3Atrue%2C%22usersSearchTerm%22%3A%22Chicago%20IL%22%2C%22regionSelection%22%3A%5B%7B%22regionId%22%3A17426%2C%22regionType%22%3A6%7D%5D%2C%22pagination%22%3A%7B%7D%2C%22category%22%3A%22cat1%22%7D"

parsed = urllib.parse.urlparse(original_url)
query_params = urllib.parse.parse_qs(parsed.query)
state_json = query_params['searchQueryState'][0]
state = json.loads(state_json)

# Reset mp filter to avoid conflict with price
if 'mp' in state['filterState']:
    del state['filterState']['mp']

# Ranges: 0-1000, 1001-1300, 1301-1600, 1601-1900, 1901-2200, 2201-2500, 2501-2900, 2901-3500, 3501-4500, 4501-300000
ranges = [
    (None, 1000),
    (1001, 1300),
    (1301, 1600),
    (1601, 1900),
    (1901, 2200),
    (2201, 2500),
    (2501, 2900),
    (2901, 3500),
    (3501, 4500),
    (4501, 300000)
]

urls = []
for min_p, max_p in ranges:
    s = copy.deepcopy(state)
    if min_p:
        s['filterState']['price']['min'] = min_p
    if max_p:
        s['filterState']['price']['max'] = max_p
    
    url = f"https://www.zillow.com/chicago-il/rentals/?searchQueryState={urllib.parse.quote(json.dumps(s))}"
    urls.append(url)

with open('urls_10way.txt', 'w') as f:
    f.write("\n".join(urls))
