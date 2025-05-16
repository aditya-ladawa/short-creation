# import asyncio
# import aiohttp
# import requests
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin, urlencode


# class BensoundScraper:
#     def __init__(self, search_terms, base_url="https://www.bensound.com", sort="relevance"):
#         self.base_url = base_url.rstrip("/")
#         self.search_terms = search_terms
#         self.sort = sort
#         self.tracks = []

#         tags = search_terms.lower().split()
#         tag_params = [("tag[]", tag) for tag in tags]
#         self.search_url = f"{self.base_url}/royalty-free-music?" + urlencode(tag_params + [("type", "free"), ("sort", sort)])

#     def get_total_pages(self):
#         response = requests.get(self.search_url)
#         soup = BeautifulSoup(response.text, "html.parser")
#         pagination = soup.select("a.pagination-link")
#         if pagination:
#             try:
#                 return int(pagination[-1].text.strip())
#             except ValueError:
#                 return 1
#         return 1

#     async def fetch(self, session, url):
#         async with session.get(url) as response:
#             return await response.text()

#     async def extract_track_details(self, session, track_url):
#         html = await self.fetch(session, track_url)
#         soup = BeautifulSoup(html, "html.parser")
#         song_section = soup.select_one("div#song")

#         if not song_section:
#             return None

#         try:
#             title = song_section.select_one("h1.is-size-4").text.strip()
#             composer = song_section.select_one("h2.is-size-6 a").text.strip()
#             description_div = song_section.select_one("div.description")
#             description = " ".join(p.text.strip() for p in description_div.find_all("p"))
#         except Exception:
#             return None

#         return {
#             "title": title,
#             "composer": composer,
#             "description": description,
#             "url": track_url,
#         }

#     async def extract_tracks_from_page(self, session, page_url):
#         html = await self.fetch(session, page_url)
#         soup = BeautifulSoup(html, "html.parser")
#         track_links = soup.select("a.has-text-black")

#         tasks = []
#         for a_tag in track_links:
#             href = a_tag.get("href")
#             if href:
#                 full_url = urljoin(self.base_url, href)
#                 tasks.append(self.extract_track_details(session, full_url))

#         return await asyncio.gather(*tasks)

#     async def scrape_pages(self, max_pages=1):
#         async with aiohttp.ClientSession() as session:
#             for page in range(1, max_pages + 1):
#                 page_url = f"{self.search_url}/{page}"
#                 print(f"Scraping page {page}: {page_url}")
#                 page_tracks = await self.extract_tracks_from_page(session, page_url)
#                 self.tracks.extend([track for track in page_tracks if track])

#     def get_data(self):
#         return self.tracks


# # Example usage with user input
# async def main():
#     search_input = input("Enter search tags (e.g., 'ambient piano'): ")
#     num_pages = int(input("Enter number of pages to scrape: "))

#     scraper = BensoundScraper(search_input)
#     await scraper.scrape_pages(max_pages=num_pages)

#     data = scraper.get_data()

#     for i, track in enumerate(data, 1):
#         print(f"{i}. {track['title']} by {track['composer']}\n{track['description']}\nURL: {track['url']}\n")


# if __name__ == "__main__":
#     asyncio.run(main())


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
    print(f"Downloading from: {track_url}")

    # Setup Chrome options for automatic download
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    chrome_options.add_argument("--headless=new")  # Optional for visibility
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get(track_url)

        # Wait for the free download button to appear
        download_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/download/')]"))
        )
        print("Clicking download button...")
        download_button.click()

        # Wait for the download to finish (naive method)
        time.sleep(10)
    finally:
        driver.quit()
    print("Download finished.")


# === Main Script ===
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

    # Ask for track number instead of title
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

    download_track_with_selenium(selected["url"], download_dir)


if __name__ == "__main__":
    asyncio.run(main())
