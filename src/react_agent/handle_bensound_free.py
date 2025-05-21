import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode
import os
import time
import re

import ffmpeg
import asyncio

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

        try:
            # Title
            title = soup.select_one("div#song h1.is-size-4").text.lower().strip()

            # Composer
            composer = soup.select_one("div#song h2.is-size-6 a").text.lower().strip()

            # Description
            description_div = soup.select_one("div.description")
            description = " ".join(p.text.strip() for p in description_div.find_all("p")) if description_div else ""

            # Duration (from .details section, not #song)
            duration_text = soup.select_one("div.details > div > span:first-child").text.lower().strip()
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
                print(full_url)

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
    song_name = song_name.replace('-', '')
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
async def fetch_track(input_query: str, save_path: str, n_pages: int=2):
    search_input = str(input_query)
    num_pages = int(n_pages)

    scraper = ben_sound_scraper = BensoundScraper(input_query)
    await scraper.scrape_pages(max_pages=num_pages)

    data = scraper.get_data()

    info_string = ""
    for i, track in enumerate(data, 1):
        info_string += f"{i}. {track['title']} by {track['composer']} (Duration: {track['duration']})\n{track['description']}\nURL: {track['url']}\n\n"

    return info_string, data


async def add_bgm_to_narrated_video_async(
    video_path: str,
    bgm_path: str,
    output_path: str = None,
    bgm_volume: float = 0.3,
    narration_volume: float = 1.0,
    fade_duration: float = 1.0,
    # Sidechaincompress params
    sc_threshold: str = '-30dB',
    sc_ratio: float = 10,
    sc_attack: int = 5,     # in milliseconds
    sc_release: int = 100,  # in milliseconds
    sc_level_in: float = 1,
    sc_level_sc: float = 1,
    sc_makeup: float = None # None means omit makeup param
) -> str:
    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_BGM{ext}"

    def run_ffmpeg():
        # Probe video duration
        duration = float(ffmpeg.probe(video_path)['format']['duration'])

        # Inputs
        video_in = ffmpeg.input(video_path)
        bgm_in = ffmpeg.input(bgm_path)

        # Adjust BGM volume and apply fade out at the end
        bgm_audio = (
            bgm_in.audio
            .filter('atrim', duration=duration)
            .filter('afade', t='out', st=duration - fade_duration, d=fade_duration)
            .filter('volume', bgm_volume)
        )

        # Adjust narration volume and split for ducking
        narration_audio = video_in.audio.filter('volume', narration_volume).filter_multi_output('asplit', 2)
        narration_main = narration_audio[0]
        narration_for_ducking = narration_audio[1]

        # Build sidechaincompress args dictionary
        sc_args = dict(
            threshold=sc_threshold,
            ratio=sc_ratio,
            attack=sc_attack,
            release=sc_release,
            level_in=sc_level_in,
            level_sc=sc_level_sc,
        )
        if sc_makeup is not None:
            sc_args['makeup'] = sc_makeup

        # Apply sidechaincompress for auto-ducking
        ducked_bgm = ffmpeg.filter(
            [bgm_audio, narration_for_ducking],
            'sidechaincompress',
            **sc_args
        )

        # Mix narration with ducked BGM
        mixed_audio = ffmpeg.filter(
            [narration_main, ducked_bgm],
            'amix',
            dropout_transition=0,
            duration='shortest'
        )

        # Output final video
        (
            ffmpeg
            .output(video_in.video, mixed_audio, output_path, vcodec='copy', acodec='aac', audio_bitrate='192k')
            .overwrite_output()
            .run()
        )
        return output_path

    return await asyncio.to_thread(run_ffmpeg)




async def main():
    tracks_info_str, tracks_data = await fetch_track(
    n_pages=1,
    save_path='/home/aditya-ladawa/Aditya/z_projects/short_creation/downloads',
    input_query='ambient_piano'
    )

    print(tracks_data)

# if __name__ == "__main__":
#     asyncio.run(main())