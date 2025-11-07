import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# קבלת ה-URL כפרמטר מהפקודה שתריץ את הסקריפט
url_to_wake = sys.argv[1]

# הגדרות להרצת דפדפן כרום ב"מצב שקט" (headless) בשרתי GitHub
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

print(f"[{url_to_wake}] - Accessing URL...")
driver.get(url_to_wake)

try:
    # נחכה מקסימום 15 שניות עד שהכפתור יופיע
    wait = WebDriverWait(driver, 15)
    
    # חיפוש מדויק של הכפתור לפי הטקסט שעליו
    button_xpath = "//button[contains(., 'Yes, get this app back up!')]"
    button = wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
    
    print(f"[{url_to_wake}] - App is asleep. Found button, clicking...")
    button.click()
    print(f"[{url_to_wake}] - Clicked wake-up button.")
    
    # ניתן להוסיף המתנה נוספת כאן כדי לוודא שהאפליקציה עולה
    time.sleep(10) 
    print(f"[{url_to_wake}] - App should be awake now.")

except TimeoutException:
    # אם הכפתור לא הופיע אחרי 15 שניות - כנראה שהאפליקציה כבר ערה
    print(f"[{url_to_wake}] - Wake-up button not found. App is likely already awake.")
    
finally:
    driver.quit()
