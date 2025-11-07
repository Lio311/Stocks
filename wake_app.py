import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Get the URL as a parameter from the command line
url_to_wake = sys.argv[1]

# Settings for running Chrome in headless mode on GitHub servers
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

print(f"[{url_to_wake}] - Accessing URL...")
driver.get(url_to_wake)

try:
    # Wait a maximum of 15 seconds for the button to appear
    wait = WebDriverWait(driver, 15)
    
    # Find the button precisely by its text
    button_xpath = "//button[contains(., 'Yes, get this app back up!')]"
    button = wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
    
    print(f"[{url_to_wake}] - App is asleep. Found button, clicking...")
    button.click()
    print(f"[{url_to_wake}] - Clicked wake-up button.")
    
    # We can add an extra wait here to ensure the app loads
    time.sleep(10) 
    print(f"[{url_to_wake}] - App should be awake now.")

except TimeoutException:
    # If the button didn't appear after 15 seconds - the app is likely already awake
    print(f"[{url_to_wake}] - Wake-up button not found. App is likely already awake.")
    
finally:
    driver.quit()
