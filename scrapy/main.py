from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import json
import gzip
import time
import concurrent.futures
import math

class RestaurantScraper:
    def __init__(self, location_to_search):
        # Initialize the RestaurantScraper with the location to search
        self.location_to_search = location_to_search
        # Define the output file name based on the location
        self.output_file = f'{location_to_search.replace(" ", "_")}_output_latlng.ndjson'

    def slow_scroll_to_bottom(self, driver):
        # Gradually scroll to the bottom of the page with a delay
        start_time = time.time()
        while time.time() - start_time < 25:  # Scroll for 25 seconds
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(0.5)  # Adjust the sleep duration as needed

    def scrape_restaurant_data(self, driver):
        # Extract restaurant data after scrolling to the end
        restaurant_list = []

        # Use execute_script to scroll to the end of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)  # Allow time for new content to load

        offset = 0
        while True:
            # Monitor network requests
            requests = [request for request in driver.requests if request.response and request.url.startswith('https://portal.grab.com/foodweb/v2/search')]
            if len(requests) >= 8:
                break

        for request in requests:
            res = request.response
            # Check if the content is gzipped
            if res.headers.get('Content-Encoding', '') == 'gzip':
                body_json = json.loads(gzip.decompress(res.body).decode('utf-8'))
            else:
                body_json = json.loads(res.body.decode('utf-8'))

            search_merchants = body_json.get('searchResult', {}).get('searchMerchants', [])
            for restaurant in search_merchants:
                # Extract relevant information for each restaurant
                _data = {}
                _data['Restaurant ID'] = restaurant.get('id', '')
                _data['Restaurant Name'] = restaurant.get('address', {}).get('name', '')
                _data['Restaurant latitude '] = restaurant.get('latlng', {}).get('latitude', '')
                _data['Restaurant longitude'] = restaurant.get('latlng', {}).get('longitude', '')
                _data['Estimate time of Delivery'] = restaurant.get('estimatedDeliveryTime', '')
                _data['Restaurant Cuisine'] = restaurant.get('merchantBrief', {}).get('cuisine', '')
                _data['Restaurant Notice'] = restaurant.get('merchantBrief', {}).get('openHours', '')
                _data['Image Link of the Restaurant'] = restaurant.get('merchantBrief', {}).get('photoHref', '')
                _data['Restaurant Distance from Delivery Location'] = restaurant.get('merchantBrief', {}).get('distanceInKm', '')
                _data['Restaurant Rating'] = restaurant.get('merchantBrief', {}).get('rating', '')
                
                # Extract promo information
                promo_info = restaurant.get('merchantBrief', {}).get('promo', {})
                _data['Is promo available'] = promo_info.get('hasPromo', False)
                _data['Promotional Offers Listed for the Restaurant'] = promo_info.get('description', 'None') if _data['Is promo available'] else 'None'

                # Calculate estimated delivery fee
                _data['estimateDeliveryFee'] = float(_data['Restaurant Distance from Delivery Location']) * 3 if _data['Restaurant Distance from Delivery Location'] else None

                restaurant_list.append(_data)

        return restaurant_list

    def run_scraper(self):
        # Use SeleniumWire with Chrome
        chrome_options = Options()
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--proxy-server="direct://"')
        chrome_options.add_argument('--proxy-bypass-list=*')
        chrome_options.add_argument('--disable-web-security')  # Disable web security to handle SSL verification issues

        # Specify the path to the Selenium Wire CA certificate
        chrome_options.add_argument(r'--ca-certificate=C:\Users\KH Jaideep\Desktop\scrap\ca.crt')

        # Create a custom user data profile with SSL verification disabled
        chrome_options.add_argument(r'--user-data-dir=C:\Users\KH Jaideep\Desktop\scrap\custom_chrome_profile')

        # Initialize the webdriver with custom options
        driver = webdriver.Chrome(seleniumwire_options={'disable_certificate_verification': True}, options=chrome_options)
        url = "https://food.grab.com/sg/en"
        driver.get(url)

        # Search for a location
        search_bar = driver.find_element(By.ID, "location-input")
        submit_button = driver.find_element(By.CSS_SELECTOR, '.ant-btn.submitBtn___2roqB.ant-btn-primary')

        if search_bar:
            # Clear the search bar, enter the location, and submit the search
            search_bar.clear()
            search_bar.send_keys(self.location_to_search)
            time.sleep(5)
            search_bar.send_keys(Keys.ENTER)
            time.sleep(5)
            submit_button.click()
            time.sleep(5)

        # Slowly scroll to the bottom of the page
        self.slow_scroll_to_bottom(driver)

        # Scrape restaurant data
        restaurant_list = self.scrape_restaurant_data(driver)

        # Save data to gzip-compressed NDJSON file        
        gzipped_file = f'{self.output_file}.gz'
        with gzip.open(gzipped_file, 'wt', encoding='utf-8') as f:
            # Write each restaurant data as a JSON object to the output file
            for restaurant in restaurant_list:
                json.dump(restaurant, f, ensure_ascii=False)
                f.write('\n')
        print(f'\nDone. Output saved to {gzipped_file}')
        
    
# "To check Quality control" 
    
# def perform_qc_checks(self, restaurant_list):
#         for restaurant in restaurant_list:
#             # Data Integrity Check
#             if not all(field in restaurant for field in ['Restaurant ID', 'Restaurant Name', 'Restaurant latitude ', 'Restaurant longitude']):
#                 print("Data integrity check failed for restaurant:", restaurant)
            
#             # Completeness Check
#             if any(restaurant[field] == '' for field in ['Restaurant ID', 'Restaurant Name', 'Restaurant latitude ', 'Restaurant longitude']):
#                 print("Completeness check failed for restaurant:", restaurant)

#             # Accuracy Check (Example: comparing estimated delivery fee with calculated value)
#             if 'Restaurant Distance from Delivery Location' in restaurant and 'estimateDeliveryFee' in restaurant:
#                 calculated_fee = float(restaurant['Restaurant Distance from Delivery Location']) * 3
#                 if not math.isclose(calculated_fee, restaurant['estimateDeliveryFee'], rel_tol=1e-5):
#                     print("Accuracy check failed for estimated delivery fee of restaurant:", restaurant)

#         # Error Handling (Example: checking for empty restaurant list)
#         if not restaurant_list:
#             print("Error: No restaurants found for location:", self.location_to_search)

def main():
    # List of locations to search for restaurants
    locations_to_search = ["Ang Mo Kio Avenue 10, #01-1574, Singapore, 560456", "Choa Chu Kang North 6, Singapore, 689577"]

    # Create a process pool for parallel execution
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # Submit scraping tasks for each location
        for location in locations_to_search:
            # Create a RestaurantScraper instance for the current location
            scraper_instance = RestaurantScraper(location)
            # Run the scraper for the current location
            scraper_instance.run_scraper()

if __name__ == "__main__":
    main()
