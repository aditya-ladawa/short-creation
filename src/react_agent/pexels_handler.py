import os
import asyncio
import requests
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate

from pexels_apis import PexelsAPI
from react_agent.utils import extract_video_data, sanitize_filename, extract_video_name
from react_agent.structures import PexelsVideoMultiMatch, VideoMetadata

load_dotenv()

pexels = PexelsAPI(os.environ.get('PEXELS_API_KEY'))


async def search_and_validate_videos(section, model, section_dir: Path) -> Tuple[List[VideoMetadata], List[dict]]:
    search_query = section.visual.scene
    max_retries = 5
    retry_count = 0
    validated_videos = []
    failed_sections = []

    while retry_count < max_retries:
        try:
            print(f"\n🔍 Search attempt {retry_count + 1} with query: '{search_query}'")

            search_params = {
                "query": search_query,
                "orientation": "portrait",
                "size": "medium",
                "page": 1,
                "per_page": 10,
            }

            pexels_response = pexels.search_videos(search_params)
            if pexels_response.get("status_code") != 200:
                raise ValueError(f"Pexels API returned {pexels_response.get('status_code')}")

            videos_data = extract_video_data(pexels_response)
            if not videos_data:
                raise ValueError("No videos returned from Pexels")

            print(f"🎥 Retrieved {len(videos_data)} videos from Pexels for query '{search_query}'")
            # for vid in videos_data:
            #     print(f" - Name: {extract_video_name(vid['video_url'])}")
            
            video_dict = {
                str(video['id']): extract_video_name(video['video_url'])
                for video in videos_data
            }

            video_entries = "\n".join([f"{k}: {v}" for k, v in video_dict.items()])

            # Call LLM to select best matches
            system_prompt = f"""You are an expert video assistant.

                            Given the script section:
                            {section.text}

                            And the search query used:
                            {search_query}

                            Here are some matching videos received from Pexels API in the format 'id':'video_name'.
                            {video_entries}

                            Choose 3-6 MOST relevant videos for this section. Respond with a list of matches where each item contains "video_id" and "video_name"."""

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
            ])

            get_matching_videos = prompt | model.with_structured_output(PexelsVideoMultiMatch)
            result: PexelsVideoMultiMatch = await get_matching_videos.ainvoke({
                "section_text": section.text,
                "search_query": search_query,
                "video_entries": video_entries
            })

            for match in result.matches:
                matching_video = next((v for v in videos_data if str(v["id"]) == match["video_id"]), None)
                if not matching_video:
                    continue

                video_meta = await download_video_from_metadata(matching_video, match, section_dir, section.section, search_query)
                if video_meta:
                    validated_videos.append(video_meta)

            if validated_videos:
                break
            else:
                raise ValueError("No videos were successfully downloaded for this section")

        except Exception as e:
            retry_count += 1
            print(f"⚠️ Retry {retry_count}/{max_retries} for query '{search_query}': {str(e)}")

            if retry_count >= max_retries:
                failed_sections.append({
                    "section": section.section,
                    "error": str(e),
                    "query": search_query
                })
            elif "No videos returned from Pexels" in str(e):
                print("🔁 Generalizing query...")
                search_query = await model.ainvoke(f"Suggest a more general search query for: '{search_query}'")

    return validated_videos, failed_sections

async def download_video_from_metadata(video_data, match, section_dir: Path, section_index: int, query: str) -> VideoMetadata | None:
    video_id = match["video_id"]
    video_name = match["video_name"]
    max_retries = 3
    retry = 0

    target_aspect = 9 / 16

    try:
        video_files = video_data.get("video_files", [])
        if not video_files:
            raise ValueError("No video files found")

        # Rank videos by closeness to target aspect ratio and quality preference
        quality_rank = {"hd": 0, "sd": 1, "sd-low": 2}
        sorted_videos = sorted(
            video_files,
            key=lambda v: (
                abs((v["width"] / v["height"]) - target_aspect),
                quality_rank.get(v.get("quality"), 99)
            )
        )

        for candidate in sorted_videos:
            while retry < max_retries:
                try:
                    filename = sanitize_filename(f"{section_index}_{video_id}") + '.mp4'
                    video_path = section_dir / filename
                    temp_path = video_path.with_suffix('.tmp')

                    with requests.get(candidate["link"], stream=True) as response:
                        response.raise_for_status()
                        with open(temp_path, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                    temp_path.rename(video_path)

                    return VideoMetadata(
                        script_section=section_index,
                        pexels_id=video_data["id"],
                        file_path=str(video_path),
                        search_query=query,
                        author=video_data.get("author"),
                        author_url=str(video_data.get("author_url")),
                        video_url=str(video_data.get("video_url")),
                        dimensions=f"{candidate['width']}x{candidate['height']}",
                        duration=video_data.get("duration"),
                        quality=candidate.get("quality")
                    )
                except Exception as e:
                    retry += 1
                    print(f"⚠️ Failed to download candidate video {video_id} (attempt {retry}): {str(e)}")
                    await asyncio.sleep(2 ** retry)

            print(f"❌ Candidate video format failed after {max_retries} retries, trying next best...")
            retry = 0  # reset retry count for next candidate

    except Exception as final_error:
        print(f"🚨 No downloadable formats found for video {video_id}: {str(final_error)}")

    return None
