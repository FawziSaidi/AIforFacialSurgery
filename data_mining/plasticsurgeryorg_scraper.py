import os
import time
import requests
import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException

CHROMEDRIVER_PATH = "chromedriver.exe" 
OUTPUT_DIR = "rhinoplasty_images"
CSV_FILE = "rhinoplasty_datamined.csv"
BASE_URL = "https://www.plasticsurgery.org/photo-gallery/procedure/rhinoplasty"

def setup_chrome_options():
    options = Options()
    # options.add_argument("--headless")  # Uncomment to run headless (without opening a browser window)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return options

def initialize_driver():
    service = Service(CHROMEDRIVER_PATH)
    options = setup_chrome_options()
    return webdriver.Chrome(service=service, options=options)

def create_output_directory():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def download_image(img_url, save_path):
    try:
        response = requests.get(img_url)
        response.raise_for_status()
        with open(save_path, 'wb') as file:
            file.write(response.content)
    except requests.RequestException as e:
        print(f"Failed to download {img_url}: {e}")

def write_to_csv(data):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

def dismiss_popup(driver):
    try:
        dismiss_button = driver.find_element(By.CLASS_NAME, "dismiss")
        dismiss_button.click()
        time.sleep(1)  
    except NoSuchElementException:
        print("No dismiss button found.")

def scrape_page(driver, page_url, image_count):
    driver.get(page_url)
    time.sleep(2)

    dismiss_popup(driver) 

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    before_images = soup.find_all('img', class_='procedure before')
    after_images = soup.find_all('img', class_='procedure after')

    for i, (before_img, after_img) in enumerate(zip(before_images, after_images)):
        before_url = before_img['src']
        after_url = after_img['src']

        before_save_path = os.path.join(OUTPUT_DIR, f"before-{image_count + i + 1}.jpg")
        after_save_path = os.path.join(OUTPUT_DIR, f"after-{image_count + i + 1}.jpg")

        download_image(before_url, before_save_path)
        download_image(after_url, after_save_path)

        case_url = before_img.find_parent('a')['href']
        driver.get(case_url)
        time.sleep(2)
        case_soup = BeautifulSoup(driver.page_source, 'html.parser')

        description_div = case_soup.find('div', class_='displayed-answer')
        description = description_div.text.strip() if description_div else "No description available"

        surgeon_info_div = case_soup.find('div', class_='surgeon-info-case')
        surgeon_name = surgeon_info_div.find('a').text.strip() if surgeon_info_div else "Unknown"
        location = surgeon_info_div.find('p').text.strip() if surgeon_info_div else "Unknown"

        case_number = case_url.split('/')[-1]

        # Write to CSV
        data = {
            "PictureOfBefore": f"before-{image_count + i + 1}.jpg",
            "PictureOfAfter": f"after-{image_count + i + 1}.jpg",
            "SurgeonInfo": surgeon_name,
            "Location": location,
            "Description": description,
            "CaseNumber": case_number
        }
        write_to_csv(data)

        print(f"Downloaded: before-{image_count + i + 1}.jpg and after-{image_count + i + 1}.jpg")

    return image_count + len(before_images)

def main():
    create_output_directory()
    driver = initialize_driver()
    current_page = BASE_URL
    image_count = 0

    while True:
        image_count = scrape_page(driver, current_page, image_count)

        try:
            # Return to the main URL before looking for the "Next" button
            driver.get(current_page)
            time.sleep(5)

            # Look for the "Next" button using the correct XPath
            next_button = driver.find_element(By.XPATH, "//div[@class='results-pager']/ul/li/a[text()='Next']")
            current_page = next_button.get_attribute("href")

            if not current_page:
                print("No more pages found.")
                break

            next_button.click()  # Click to go to the next page
            time.sleep(2)  # Give time for the next page to load
        except Exception as e:
            print(f"No more pages found or error: {e}")
            break

    driver.quit()

if __name__ == "__main__":
    main()