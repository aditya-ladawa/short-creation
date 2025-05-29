import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode
import os
import time
import re

import ffmpeg

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

        tags = search_terms.split()
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

        try:
            # Title
            title = soup.select_one("div#song h1.is-size-4").text.strip()

            # Composer
            composer = soup.select_one("div#song h2.is-size-6 a").text.strip()

            # Description
            description_div = soup.select_one("div.description")
            description = " ".join(p.text.strip() for p in description_div.find_all("p")) if description_div else ""

            # Duration (from .details section, not #song)
            duration_text = soup.select_one("div.details > div > span:first-child").text.strip()
            minutes, seconds = map(int, duration_text.split(':'))
            duration_seconds = minutes * 60 + seconds

        except Exception as e:
            print(f"Error extracting track from {track_url}: {e}")
            return None

        return {
            "title": title,
            "composer": composer,
            "duration": duration_seconds,
            "description": description,
            "url": track_url,
        }

    async def extract_tracks_from_page(self, session, page_url):
        html = await self.fetch(session, page_url)
        soup = BeautifulSoup(html, "html.parser")

        # Find all containers that hold track links
        track_containers = soup.select("div.grid-container.result-container.px-5")

        tasks = []
        for container in track_containers:
            # Each container should have a link to the track page
            a_tag = container.find("a", href=True)
            if a_tag:
                href = a_tag["href"]
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
    song_name = track_url.rstrip('/').split('/')[-1].replace('-', '')
    attribution_filename = os.path.join(download_dir, f"{song_name}.txt")

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
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--window-size=1920,1080")



    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    driver.get(track_url)
    print(f"Opened page: {track_url}")

    try:
        wait = WebDriverWait(driver, 20)

        # Accept cookies if button exists
        try:
            settings_button = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.button.is-outlined.cookies-consent-link")))
            settings_button.click()
            print("Clicked 'Settings'")

            accept_button = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.submit-cookies-consent.cookies-accept-all")))
            accept_button.click()
            print("Accepted cookies")
        except Exception:
            print("Cookie popup not found or already accepted.")

        # Click Free Download
        free_download_span = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[contains(text(),'Free download') and contains(@class, 'has-text-centered')]")))
        free_download_span.find_element(By.XPATH, "..").click()
        print("Clicked 'Free download'")

        # Click Final Download Button
        download_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.button.is-success.free-download.is-outlined.my-3.px-6.py-5.is-size-6.is-borderless.has-text-weight-bold")))
        download_button.click()
        print("Clicked 'Download music and get Attribution text'")

        # Wait for file download
        print("Waiting for download to complete...")
        wait_time = 0
        while wait_time < 60:
            time.sleep(1)
            wait_time += 1
            if not any(f.endswith(".crdownload") or f.endswith(".part") for f in os.listdir(download_dir)):
                break

        print("Waiting a few seconds for attribution text to load...")
        time.sleep(5)

        # Extract attribution div
        # Wait for attribution wrapper div to be present
        attribution_wrapper = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.orfium-code-wrapper.is-flex.is-justify-content-space-between.is-align-items-center")
        ))

        # Find the inner column div containing the text blocks
        attribution_div = attribution_wrapper.find_element(By.CSS_SELECTOR, "div.is-flex.is-flex-direction-column")

        # Extract all child div texts inside the attribution div
        child_divs = attribution_div.find_elements(By.XPATH, "./div")
        div_texts = [div.text.strip() for div in child_divs]

        # Join all lines into one attribution text
        attribution_text = "\n".join(div_texts)

        print("==== Attribution Text Extracted ====")
        print(attribution_text)
        print("====================================")

        # Extract license code robustly
        import re
        match = re.search(r"License code:\s*([A-Z0-9]+)", attribution_text)
        license_code = match.group(1) if match else "Not found"

        # Save attribution to file as before
        with open(attribution_filename, "w", encoding='utf-8') as f:
            f.write(attribution_text + "\n\n")
            f.write(f"Extracted License Code: {license_code}\n")

        print(f"Saved attribution and license to {attribution_filename}")

        # Return both separately
        return attribution_text, license_code

    except Exception as e:
        print(f"Error during selenium interaction: {e}")
        driver.save_screenshot("selenium_error.png")
        return "Error occurred."
    finally:
        driver.quit()



# === Main Script ===
async def fetch_track(input_query: str, n_pages: int=2):
    scraper = BensoundScraper(input_query)
    await scraper.scrape_pages(max_pages=n_pages)
    data = scraper.get_data()

    info_string = ""
    for i, track in enumerate(data, 1):
        info_string += f"{i}. {track['title']} by {track['composer']} (Duration: {track['duration']})\n{track['description']}\nURL: {track['url']}\n\n"

    return info_string, data

async def main():
    query = input("Enter search query: ").strip()
    n_pages = int(input("Enter number of pages to scrape: ").strip())

    # Fetch tracks info
    info_str, tracks = await fetch_track(query, n_pages)
    print("\nAvailable tracks:\n")
    print(info_str)

    track_no = int(input(f"Enter track number to download (1-{len(tracks)}): ").strip())
    if not (1 <= track_no <= len(tracks)):
        print("Invalid track number")
        return

    track_to_download = tracks[track_no - 1]
    download_dir = os.path.abspath("downloads")
    os.makedirs(download_dir, exist_ok=True)

    print(f"Downloading track '{track_to_download['title']}' by {track_to_download['composer']}...")
    attribution_text, license_code = download_track_with_selenium(track_to_download['url'], download_dir)

    print("\n✅ Attribution Text:\n")
    print(attribution_text)

    print("\n🔐 Extracted License Code:")
    print(license_code)


# if __name__ == "__main__":
#     asyncio.run(main())