import json
import urllib.parse
import copy

original_url = "https://www.zillow.com/chicago-il/rentals/?searchQueryState=%7B%22isMapVisible%22%3Atrue%2C%22mapBounds%22%3A%7B%22north%22%3A42.13769363060134%2C%22south%22%3A41.52888309438494%2C%22east%22%3A-87.19223863085938%2C%22west%22%3A-88.27164536914063%7D%2C%22filterState%22%3A%7B%22sort%22%3A%7B%22value%22%3A%22paymenta%22%7D%2C%22price%22%3A%7B%22min%22%3Anull%2C%22max%22%3A300000%7D%2C%22mp%22%3A%7B%22min%22%3Anull%7D%2C%22fr%22%3A%7B%22value%22%3Atrue%7D%2C%22fsba%22%3A%7B%22value%22%3Afalse%7D%2C%22fsbo%22%3A%7B%22value%22%3Afalse%7D%2C%22nc%22%3A%7B%22value%22%3Afalse%7D%2C%22cmsn%22%3A%7B%22value%22%3Afalse%7D%2C%22auc%22%3A%7B%22value%22%3Afalse%7D%2C%22fore%22%3A%7B%22value%22%3Afalse%7D%2C%22att%22%3A%7B%22value%22%3A%22by%20owner%22%7D%7D%2C%22isListVisible%22%3Atrue%2C%22usersSearchTerm%22%3A%22Chicago%20IL%22%2C%22regionSelection%22%3A%5B%7B%22regionId%22%3A17426%2C%22regionType%22%3A6%7D%5D%2C%22pagination%22%3A%7B%7D%2C%22category%22%3A%22cat1%22%7D"

parsed = urllib.parse.urlparse(original_url)
query_params = urllib.parse.parse_qs(parsed.query)
state_json = query_params['searchQueryState'][0]
state = json.loads(state_json)

# URL 1: $0 - $1400
state1 = copy.deepcopy(state)
state1['filterState']['mp'] = {'max': 1400}
url1 = f"https://www.zillow.com/chicago-il/rentals/?searchQueryState={urllib.parse.quote(json.dumps(state1))}"

# URL 2: $1401 - $2100
state2 = copy.deepcopy(state)
state2['filterState']['mp'] = {'min': 1401, 'max': 2100}
url2 = f"https://www.zillow.com/chicago-il/rentals/?searchQueryState={urllib.parse.quote(json.dumps(state2))}"

# URL 3: $2101 - $300,000
state3 = copy.deepcopy(state)
state3['filterState']['mp'] = {'min': 2101}
state3['filterState']['price'] = {'max': 300000}
url3 = f"https://www.zillow.com/chicago-il/rentals/?searchQueryState={urllib.parse.quote(json.dumps(state3))}"

with open('urls_3way.txt', 'w') as f:
    f.write(f"{url1}\n{url2}\n{url3}")
