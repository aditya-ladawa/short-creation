import os
import time
import random
import http.client as httplib
import httplib2

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow
from dotenv import load_dotenv
from typing import Optional
load_dotenv()

CLIENT_SECRETS_FILE = os.environ.get("GOOGLE_CLIENT_SECRET_PATH")
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"

def get_authenticated_service():
    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE, scope=YOUTUBE_UPLOAD_SCOPE)
    storage = Storage("youtube-oauth2.json")
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, None)
    return build("youtube", "v3", http=credentials.authorize(httplib2.Http()))


def youtube_upload_short(file_path, title, description, keywords="", category="22", privacy="public") -> Optional[str]:
    youtube = get_authenticated_service()
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": keywords.split(",") if keywords else [],
            "categoryId": category,
            # # Remove or adjust defaultLanguage if not needed
            # "defaultLanguage": "no"
        },
        "status": {
            "privacyStatus": privacy,
            "madeForKids": False,
            # Optional explicit self-declaration:
            "selfDeclaredMadeForKids": False  
        },
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    retry = 0
    while response is None:
        try:
            _, response = request.next_chunk()
            if response and "id" in response:
                link = f"https://youtube.com/shorts/{response['id']}"
                return link
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                retry += 1
                if retry > 10:
                    print("❌ Too many retries.")
                    break
                sleep = random.random() * (2 ** retry)
                print(f"Retrying in {sleep:.2f}s...")
                time.sleep(sleep)
            else:
                raise
    return None
# # 🧪 Example usage
# if __name__ == "__main__":
#     youtube_upload_short(
#         file_path="/home/aditya-ladawa/Aditya/z_projects/short_creation/my_test_files/output_reels_fades_ordered_v3/The_Guilt_Trap/FINAL_CAPTIONED_The_Guilt_Trap.mp4",
#         title="Summer vacation in California",
#         description="Had fun surfing in Santa Cruz",
#         keywords="surfing,Santa Cruz",
#         category="22",
#         privacy="private"
#     )
