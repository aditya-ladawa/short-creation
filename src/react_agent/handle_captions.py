import os
import json
from pathlib import Path
from typing import List, Dict, Tuple

import cv2
import ffmpeg
import numpy as np
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from faster_whisper import WhisperModel
from moviepy import (
    TextClip,
    CompositeVideoClip,
    ColorClip,
    VideoFileClip,
    ImageClip,
)

load_dotenv()

CAPTIONS_FONT_PATH = os.environ.get('CAPTIONS_FONT_PATH')

class VideoCaptioner:
    def __init__(self, model_size: str = 'base', device: str = "cpu", compute_type: str = 'int8'):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.subtitle_config = {
            'max_chars': 60,
            'max_words': 7,
            'max_duration': 4,
            'max_wordgap': 1.5,
        }
        self.caption_config = {
            "fontsize": 50,
            "font": CAPTIONS_FONT_PATH,
            "highlight_fontsize": 65,
            "highlight_color": 'white',
            "highlight_bg_color": (0, 0, 200),
            "highlight_padding": 10,
            "highlight_radius": 15,
            "text_position": ('center', 'bottom'),
            "text_margin": 100,
        }

    async def generate_subtitles(self, audio_file_name: str) -> List[Dict]:
        segments, _ = self.model.transcribe(audio_file_name, word_timestamps=True)
        segments = list(segments)
        return [
            {'word': word.word, 'start': word.start, 'end': word.end}
            for segment in segments for word in segment.words
        ]

    async def create_line_level_subtitles(self, word_data: List[Dict]) -> List[Dict]:
        subtitles, line, line_duration = [], [], 0
        for idx, word_info in enumerate(word_data):
            line.append(word_info)
            line_duration = line[-1]['end'] - line[0]['start']
            duration_exceeded = line_duration >= self.subtitle_config['max_duration']
            chars_exceeded = sum(len(w['word']) for w in line) >= self.subtitle_config['max_chars']
            maxgap_exceeded = (
                idx < len(word_data) - 1 and
                word_data[idx + 1]['start'] - word_info['end'] > self.subtitle_config['max_wordgap']
            )

            if duration_exceeded or chars_exceeded or maxgap_exceeded:
                if line:
                    subtitle_line = await self._create_subtitle_line(line)
                    subtitles.append(subtitle_line)
                    line, line_duration = [], 0

        if line:
            subtitle_line = await self._create_subtitle_line(line)
            subtitles.append(subtitle_line)

        return subtitles

    async def _create_subtitle_line(self, line: List[Dict]) -> Dict:
        return {
            "word": " ".join(item["word"].strip() for item in line),
            "start": line[0]["start"],
            "end": line[-1]["end"],
            "textcontents": line
        }

    async def add_captions_to_video(self, video_path: str, subtitles: List[Dict], output_path: str) -> None:
        video = VideoFileClip(video_path)
        frame_size = video.size
        all_clips = [video]

        for line in subtitles:
            word_clips, highlight_boxes = await self._create_caption_clips(line, frame_size)
            all_clips.extend(highlight_boxes + word_clips)

        final_video = CompositeVideoClip(all_clips).with_audio(video.audio)
        final_video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")

    async def _create_caption_clips(self, textJSON: Dict, framesize: Tuple[int, int]) -> Tuple[List[TextClip], List[ImageClip]]:
        full_duration = textJSON['end'] - textJSON['start']
        frame_width, frame_height = framesize
        fontsize = int(frame_height * 0.050)
        line_spacing = int(fontsize * 0.10)
        x_buffer = frame_width * 0.1
        max_line_width = frame_width - 2 * x_buffer

        word_clips = []
        highlight_boxes = []

        lines = []
        current_line = []
        current_line_width = 0
        current_line_height = 0

        for wordJSON in textJSON['textcontents']:
            word = wordJSON['word']
            start = wordJSON['start']
            end = wordJSON['end']
            duration = end - start

            padded_height = int(fontsize * 1.3)

            word_clip = TextClip(
                text=word,
                font=self.caption_config["font"],
                font_size=fontsize,
                color=self.caption_config["highlight_color"],
                size=(None, padded_height)
            )
            word_width, word_height = word_clip.size

            space_clip = TextClip(
                text=' ',
                font=self.caption_config["font"],
                font_size=fontsize,
                color=self.caption_config["highlight_color"],
                size=(None, padded_height)
            )
            space_width, _ = space_clip.size

            if current_line_width + word_width <= max_line_width:
                current_line.append({
                    'word': word,
                    'start': start,
                    'end': end,
                    'duration': duration,
                    'clip': word_clip,
                    'width': word_width,
                    'height': word_height
                })
                current_line_width += word_width + space_width
                current_line_height = max(current_line_height, word_height)
            else:
                lines.append({
                    'words': current_line,
                    'width': current_line_width,
                    'height': current_line_height
                })
                current_line = [{
                    'word': word,
                    'start': start,
                    'end': end,
                    'duration': duration,
                    'clip': word_clip,
                    'width': word_width,
                    'height': word_height
                }]
                current_line_width = word_width + space_width
                current_line_height = word_height

        if current_line:
            lines.append({
                'words': current_line,
                'width': current_line_width,
                'height': current_line_height
            })

        total_text_height = sum(line['height'] for line in lines) + line_spacing * (len(lines) - 1)
        bottom_margin = int(frame_height * 0.08)
        y_start = frame_height - total_text_height - bottom_margin

        for line in lines:
            line_width = line['width']
            line_height = line['height']
            x_start = (frame_width - line_width) / 2
            x_pos = x_start
            for word_info in line['words']:
                word_clip = word_info['clip'] \
                    .with_start(textJSON['start']) \
                    .with_duration(full_duration) \
                    .with_position((x_pos, y_start))
                word_clips.append(word_clip)

                # Add box with padding
                padding_x = int(fontsize * 0.2)
                padding_y = int(fontsize * 0.1)
                box_width = int(word_info['width'] + 2 * padding_x)
                box_height = int(word_info['height'] + 2 * padding_y)
                radius = int(word_info['height'] * 0.2)

                box_img = self._create_rounded_box_cv(
                    (box_width, box_height),
                    radius=radius,
                    color=self.caption_config['highlight_bg_color']
                )

                box_clip = ImageClip(box_img, is_mask=False) \
                    .with_start(word_info['start']) \
                    .with_duration(word_info['duration']) \
                    .with_position((x_pos - padding_x, y_start - padding_y)) \
                    .with_opacity(0.6)

                highlight_boxes.append(box_clip)
                x_pos += word_info['width'] + space_width
            y_start += line_height + line_spacing

        return word_clips, highlight_boxes

    def _create_rounded_box_cv(self, size: Tuple[int, int], radius: int, color: Tuple[int, int, int]) -> np.ndarray:
        width, height = size
        mask = np.zeros((height, width, 4), dtype=np.uint8)
        box = np.zeros((height, width), dtype=np.uint8)

        cv2.rectangle(box, (radius, 0), (width - radius, height), 255, -1)
        cv2.rectangle(box, (0, radius), (width, height - radius), 255, -1)
        cv2.circle(box, (radius, radius), radius, 255, -1)
        cv2.circle(box, (width - radius, radius), radius, 255, -1)
        cv2.circle(box, (radius, height - radius), radius, 255, -1)
        cv2.circle(box, (width - radius, height - radius), radius, 255, -1)

        for i in range(3):
            mask[:, :, i] = color[i]
        mask[:, :, 3] = box

        return mask


    async def save_subtitles_to_json(self, subtitles: List[Dict], output_path: str) -> None:
        with open(output_path, 'w') as f:
            json.dump(subtitles, f, indent=4)

    async def extract_audio_from_video(self, video_path: str, output_audio_path: str = None) -> str:
        """
        Extracts audio from a video file and saves it as an MP3.
        Returns the path to the extracted audio file.
        """
        video_path = Path(video_path)
        output_audio = Path(output_audio_path) if output_audio_path else video_path.with_suffix('.mp3')
        
        input_stream = ffmpeg.input(str(video_path))
        ffmpeg.output(input_stream.audio, str(output_audio), acodec='libmp3lame', audio_bitrate='192k')\
              .overwrite_output()\
              .run(quiet=True)

        return str(output_audio)




# async def main():
#     # Initialize captioner
#     captioner = VideoCaptioner()
    
#     # Define file paths
#     video_file = "/home/aditya-ladawa/Aditya/z_projects/short_creation/src/react_agent/output_reels_fades_ordered_v3/The_Power_of_Silence_Why_Saying_Less_Makes_You_Stronger/The_Power_of_Silence_Why_Saying_Less_Makes_You_Stronger_final_ordered_reel.mp4"

#     output_video = "/home/aditya-ladawa/Aditya/z_projects/short_creation/src/react_agent/output_reels_fades_ordered_v3/The_Power_of_Silence_Why_Saying_Less_Makes_You_Stronger/CAPTIONED_The_Power_of_Silence_Why_Saying_Less_Makes_You_Stronger_final_ordered_reel.mp4"

#     output_json = "/home/aditya-ladawa/Aditya/z_projects/short_creation/src/react_agent/output_reels_fades_ordered_v3/The_Power_of_Silence_Why_Saying_Less_Makes_You_Stronger/The_Power_of_Silence_Why_Saying_Less_Makes_You_Stronger_final_ordered_reel.json"

#     # Extract audio from video
#     audio_file = await captioner.extract_audio_from_video(video_file)

#     # Generate subtitles
#     word_segments = await captioner.generate_subtitles(audio_file)
#     line_subtitles = await captioner.create_line_level_subtitles(word_segments)

#     # Save subtitles to JSON
#     await captioner.save_subtitles_to_json(line_subtitles, output_json)

#     # Add captions to video
#     await captioner.add_captions_to_video(video_file, line_subtitles, output_video)

#     print("Done. Captioned video saved at:", output_video)

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())