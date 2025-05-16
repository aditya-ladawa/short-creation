from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

def download_track_with_selenium(track_url, download_dir):
    # Extract song name from URL for attribution file and file existence check
    # URL example: https://www.bensound.com/royalty-free-music/track/echo-of-sadness-cinematic-fantasy
    song_name = track_url.rstrip('/').split('/')[-1]
    attribution_filename = os.path.join(download_dir, f"{song_name}_attribution.txt")

    # Check if attribution file already exists -> assume download done, skip
    if os.path.exists(attribution_filename):
        print(f"Attribution file already exists for '{song_name}'. Skipping download.")
        with open(attribution_filename, 'r', encoding='utf-8') as f:
            attribution_text = f.read()
        return attribution_text

    chrome_options = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    # chrome_options.add_argument("--headless")  # Uncomment to run headless

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(track_url)
    print(f"Opened page: {track_url}")

    try:
        wait = WebDriverWait(driver, 20)

        # (Same cookie consent steps as before)
        settings_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.button.is-outlined.cookies-consent-link")
        ))
        settings_button.click()
        print("Clicked 'Settings' button")

        reject_cookies_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.button.close-modal.submit-cookies-consent.cookies-decline-all")
        ))
        reject_cookies_button.click()
        print("Clicked 'Reject Optional Cookies' button")

        free_download_span = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[contains(text(),'Free download') and contains(@class, 'has-text-centered')]")
        ))
        free_download_span.find_element(By.XPATH, "..").click()
        print("Clicked 'Free download' button")

        download_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.button.is-success.free-download.is-outlined.my-3.px-6.py-5.is-size-6.is-borderless.has-text-weight-bold")
        ))
        download_button.click()
        print("Clicked 'Download music and get Attribution text' button")

        # Before waiting for download, check if the actual audio file already exists to skip download
        # Since the downloaded file name might not be directly known, you might check for any new files,
        # but here we will just wait for download to complete.

        print("Waiting for download to complete...")
        download_complete = False
        wait_time = 0
        while not download_complete and wait_time < 60:
            time.sleep(1)
            wait_time += 1
            files = os.listdir(download_dir)
            if any(fname.endswith(".crdownload") or fname.endswith(".part") for fname in files):
                continue
            else:
                download_complete = True

        if download_complete:
            print("Download completed.")
        else:
            print("Download may not have completed after 60 seconds.")

        # Extract attribution text
        attribution_div = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.is-flex.is-flex-direction-column")
        ))

        attribution_text = attribution_div.text
        print("Attribution text found:")
        print(attribution_text)

        # Find license line
        lines = attribution_text.split('\n')
        license_line = next((line for line in lines if "License code:" in line), None)

        if license_line and "Sorry" in license_line:
            print("Warning: License code indicates an error or missing data.")
        elif not license_line:
            license_line = "License code: Not found"

        # Save attribution text with song name as filename
        with open(attribution_filename, "w", encoding="utf-8") as f:
            f.write(attribution_text + "\n\n")
            f.write("Extracted License Code:\n" + (license_line or "None") + "\n")

        print(f"Attribution and license info saved to {attribution_filename}")

        return attribution_text

    except Exception as e:
        print(f"Error during selenium interaction: {e}")
        driver.save_screenshot("selenium_error.png")
    finally:
        driver.quit()


download_dir = "/home/aditya-ladawa/Aditya/z_projects/short_creation/downloads"
track_url = "https://www.bensound.com/royalty-free-music/track/echo-of-sadness-cinematic-fantasy"

attribution_text = download_track_with_selenium(track_url, download_dir)
print("Final Attribution Text:\n", attribution_text)
