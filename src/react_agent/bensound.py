# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import time
# import os

# def download_track_with_selenium(track_url, download_dir):
#     # Extract song name from URL for attribution file and file existence check
#     # URL example: https://www.bensound.com/royalty-free-music/track/echo-of-sadness-cinematic-fantasy
#     song_name = track_url.rstrip('/').split('/')[-1]
#     attribution_filename = os.path.join(download_dir, f"{song_name}_attribution.txt")

#     # Check if attribution file already exists -> assume download done, skip
#     if os.path.exists(attribution_filename):
#         print(f"Attribution file already exists for '{song_name}'. Skipping download.")
#         with open(attribution_filename, 'r', encoding='utf-8') as f:
#             attribution_text = f.read()
#         return attribution_text

#     chrome_options = Options()
#     prefs = {
#         "download.default_directory": download_dir,
#         "download.prompt_for_download": False,
#         "directory_upgrade": True,
#         "safebrowsing.enabled": True
#     }
#     chrome_options.add_experimental_option("prefs", prefs)
#     # chrome_options.add_argument("--headless")  # Uncomment to run headless

#     driver = webdriver.Chrome(options=chrome_options)
#     driver.get(track_url)
#     print(f"Opened page: {track_url}")

#     try:
#         wait = WebDriverWait(driver, 20)

#         # (Same cookie consent steps as before)
#         settings_button = wait.until(EC.element_to_be_clickable(
#             (By.CSS_SELECTOR, "button.button.is-outlined.cookies-consent-link")
#         ))
#         settings_button.click()
#         print("Clicked 'Settings' button")

#         reject_cookies_button = wait.until(EC.element_to_be_clickable(
#             (By.CSS_SELECTOR, "button.button.close-modal.submit-cookies-consent.cookies-decline-all")
#         ))
#         reject_cookies_button.click()
#         print("Clicked 'Reject Optional Cookies' button")

#         free_download_span = wait.until(EC.element_to_be_clickable(
#             (By.XPATH, "//span[contains(text(),'Free download') and contains(@class, 'has-text-centered')]")
#         ))
#         free_download_span.find_element(By.XPATH, "..").click()
#         print("Clicked 'Free download' button")

#         download_button = wait.until(EC.element_to_be_clickable(
#             (By.CSS_SELECTOR, "button.button.is-success.free-download.is-outlined.my-3.px-6.py-5.is-size-6.is-borderless.has-text-weight-bold")
#         ))
#         download_button.click()
#         print("Clicked 'Download music and get Attribution text' button")

#         # Before waiting for download, check if the actual audio file already exists to skip download
#         # Since the downloaded file name might not be directly known, you might check for any new files,
#         # but here we will just wait for download to complete.

#         print("Waiting for download to complete...")
#         download_complete = False
#         wait_time = 0
#         while not download_complete and wait_time < 60:
#             time.sleep(1)
#             wait_time += 1
#             files = os.listdir(download_dir)
#             if any(fname.endswith(".crdownload") or fname.endswith(".part") for fname in files):
#                 continue
#             else:
#                 download_complete = True

#         if download_complete:
#             print("Download completed.")
#         else:
#             print("Download may not have completed after 60 seconds.")

#         # Extract attribution text
#         attribution_div = wait.until(EC.presence_of_element_located(
#             (By.CSS_SELECTOR, "div.is-flex.is-flex-direction-column")
#         ))

#         attribution_text = attribution_div.text
#         print("Attribution text found:")
#         print(attribution_text)

#         # Find license line
#         lines = attribution_text.split('\n')
#         license_line = next((line for line in lines if "License code:" in line), None)

#         if license_line and "Sorry" in license_line:
#             print("Warning: License code indicates an error or missing data.")
#         elif not license_line:
#             license_line = "License code: Not found"

#         # Save attribution text with song name as filename
#         with open(attribution_filename, "w", encoding="utf-8") as f:
#             f.write(attribution_text + "\n\n")
#             f.write("Extracted License Code:\n" + (license_line or "None") + "\n")

#         print(f"Attribution and license info saved to {attribution_filename}")

#         return attribution_text

#     except Exception as e:
#         print(f"Error during selenium interaction: {e}")
#         driver.save_screenshot("selenium_error.png")
#     finally:
#         driver.quit()


# download_dir = "/home/aditya-ladawa/Aditya/z_projects/short_creation/downloads"
# track_url = "https://www.bensound.com/royalty-free-music/track/echo-of-sadness-cinematic-fantasy"

# attribution_text = download_track_with_selenium(track_url, download_dir)
# print("Final Attribution Text:\n", attribution_text)



import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode
import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class BensoundScraper:
    def __init__(self, search_terms, base_url="https://www.bensound.com", sort="relevance"):
        self.base_url = base_url.rstrip("/")
        self.search_terms = search_terms
        self.sort = sort
        self.tracks = []

        tags = search_terms.lower().split()
        tag_params = [("tag[]", tag) for tag in tags]
        self.search_url = f"{self.base_url}/royalty-free-music?" + urlencode(tag_params + [("type", "free"), ("sort", sort)])

    def get_total_pages(self):
        response = requests.get(self.search_url)
        soup = BeautifulSoup(response.text, "html.parser")
        pagination = soup.select("a.pagination-link")
        if pagination:
            try:
                return int(pagination[-1].text.strip())
            except ValueError:
                return 1
        return 1

    async def fetch(self, session, url):
        async with session.get(url) as response:
            return await response.text()

    async def extract_track_details(self, session, track_url):
        html = await self.fetch(session, track_url)
        soup = BeautifulSoup(html, "html.parser")
        song_section = soup.select_one("div#song")

        if not song_section:
            return None

        try:
            title = song_section.select_one("h1.is-size-4").text.strip()
            composer = song_section.select_one("h2.is-size-6 a").text.strip()
            description_div = song_section.select_one("div.description")
            description = " ".join(p.text.strip() for p in description_div.find_all("p"))
        except Exception:
            return None

        return {
            "title": title,
            "composer": composer,
            "description": description,
            "url": track_url,
        }

    async def extract_tracks_from_page(self, session, page_url):
        html = await self.fetch(session, page_url)
        soup = BeautifulSoup(html, "html.parser")
        track_links = soup.select("a.has-text-black")

        tasks = []
        for a_tag in track_links:
            href = a_tag.get("href")
            if href:
                full_url = urljoin(self.base_url, href)
                tasks.append(self.extract_track_details(session, full_url))

        return await asyncio.gather(*tasks)

    async def scrape_pages(self, max_pages=1):
        async with aiohttp.ClientSession() as session:
            for page in range(1, max_pages + 1):
                page_url = f"{self.search_url}/{page}"
                print(f"Scraping page {page}: {page_url}")
                page_tracks = await self.extract_tracks_from_page(session, page_url)
                self.tracks.extend([track for track in page_tracks if track])

    def get_data(self):
        return self.tracks


def download_track_with_selenium(track_url, download_dir):
    song_name = track_url.rstrip('/').split('/')[-1]
    attribution_filename = os.path.join(download_dir, f"{song_name}_attribution.txt")

    if os.path.exists(attribution_filename):
        print(f"Attribution file already exists for '{song_name}'. Skipping download.")
        with open(attribution_filename, 'r', encoding='utf-8') as f:
            return f.read()

    chrome_options = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    driver.get(track_url)
    print(f"Opened page: {track_url}")

    try:
        wait = WebDriverWait(driver, 20)

        settings_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.button.is-outlined.cookies-consent-link")))
        settings_button.click()
        print("Clicked 'Settings'")

        reject_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.button.close-modal.submit-cookies-consent.cookies-decline-all")))
        reject_button.click()
        print("Rejected cookies")

        free_download_span = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[contains(text(),'Free download') and contains(@class, 'has-text-centered')]")))
        free_download_span.find_element(By.XPATH, "..").click()
        print("Clicked 'Free download'")

        download_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.button.is-success.free-download.is-outlined.my-3.px-6.py-5.is-size-6.is-borderless.has-text-weight-bold")))
        download_button.click()
        print("Clicked 'Download music and get Attribution text'")

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

        attribution_div = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.is-flex.is-flex-direction-column")))

        attribution_text = attribution_div.text
        print("Attribution found.")

        lines = attribution_text.split('\n')
        license_line = next((line for line in lines if "License code:" in line), "License code: Not found")

        with open(attribution_filename, "w", encoding='utf-8') as f:
            f.write(attribution_text + "\n\n")
            f.write("Extracted License Code:\n" + license_line + "\n")

        print(f"Saved to {attribution_filename}")
        return attribution_text

    except Exception as e:
        print(f"Error during selenium interaction: {e}")
        driver.save_screenshot("selenium_error.png")
    finally:
        driver.quit()


# === Main Script ===
async def main():
    search_input = input("Enter search tags (e.g., 'ambient piano'): ")
    num_pages = int(input("Enter number of pages to scrape: "))

    scraper = BensoundScraper(search_input)
    await scraper.scrape_pages(max_pages=num_pages)

    data = scraper.get_data()

    for i, track in enumerate(data, 1):
        print(f"{i}. {track['title']} by {track['composer']}\n{track['description']}\nURL: {track['url']}\n")

    if not data:
        print("No tracks found.")
        return

    try:
        track_num = int(input(f"Enter track number to download (1 to {len(data)}): ").strip())
        if not (1 <= track_num <= len(data)):
            print("Invalid track number.")
            return
    except ValueError:
        print("Invalid input. Must be a number.")
        return

    selected = data[track_num - 1]
    print(f"Selected: {selected['title']} by {selected['composer']}")

    download_dir = os.path.abspath("downloads")
    os.makedirs(download_dir, exist_ok=True)

    attribution_text = download_track_with_selenium(selected["url"], download_dir)
    print("\nFinal Attribution Text:\n", attribution_text)


if __name__ == "__main__":
    asyncio.run(main())
