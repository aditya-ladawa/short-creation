import ffmpeg
import random
import os


BASE_VIDEOS_PATH = "/home/aditya-ladawa/Aditya/z_projects/short_creation/my_test_files/videos/" # Adjust as needed
OUTPUT_DIR_BASE = "/home/aditya-ladawa/Aditya/z_projects/short_creation/my_test_files/output_reels_fades_ordered_v3" # New output folder

os.makedirs(OUTPUT_DIR_BASE, exist_ok=True)

MIN_SEGMENT_DURATION = 3.0
MAX_SEGMENT_DURATION = 6.0
TRANSITION_DURATION = 0.6
REEL_WIDTH = 720
REEL_HEIGHT = 1280
OUTPUT_FPS = 30 

VIDEO_CODEC = 'libx264'
PRESET = 'slow'
CRF = 20
VIDEO_BITRATE = '2500k'
AUDIO_CODEC = 'aac'
AUDIO_BITRATE = '192k'

CRF = 23
PRESET_X264 = 'ultrafast'
XFADE_TRANSITIONS = ['fade']

SECTION_SILENCE = {
    'HOOK': 1.0,
    'CONCEPT': 1.0,
    'REAL-WORLD_EXAMPLE': 1.5,
    'PSYCHOLOGICAL_INSIGHT': 2.0,
    'ACTIONABLE_TIP': 0.5,
    'CTA': 0.5
}

# Define the desired order for final concatenation
SECTION_ORDER = ['HOOK', 'CONCEPT', 'REAL-WORLD_EXAMPLE', 'PSYCHOLOGICAL_INSIGHT', 'ACTIONABLE_TIP', 'CTA']


def get_duration(filename):
    try:
        probe = ffmpeg.probe(filename)
        return float(probe['format']['duration'])
    except Exception as e:
        print(f"Error probing duration for {filename}: {e}")
        return None


def apply_segment_effects(video_node):
    node = video_node.filter(
        'scale', w=f'iw*max({REEL_WIDTH}/iw,{REEL_HEIGHT}/ih)',
        h=f'ih*max({REEL_WIDTH}/iw,{REEL_HEIGHT}/ih)', eval='frame'
    )
    node = node.filter('crop', w=REEL_WIDTH, h=REEL_HEIGHT,
                       x=f'(iw-{REEL_WIDTH})/2', y=f'(ih-{REEL_HEIGHT})/2')
    node = node.filter('fps', fps=OUTPUT_FPS, round='near')
    node = node.filter('setpts', 'PTS-STARTPTS')
    return node



def create_reel_for_audio(audio_file_path, associated_video_files, output_file_path):
    section_name = os.path.splitext(os.path.basename(audio_file_path))[0]
    section_key = section_name.upper() # Key for SECTION_SILENCE and CTA check
    silence_duration = SECTION_SILENCE.get(section_key, 1.0)

    # 1. Measure audio
    audio_duration = get_duration(audio_file_path)
    if audio_duration is None:
        print(f"Skipping {audio_file_path}, could not get audio duration.")
        return None
    if not associated_video_files:
        print(f"Skipping {section_name} ({audio_file_path}), no associated video files.")
        return None

    target_duration = audio_duration + silence_duration
    print(f"\nProcessing {section_name}: audio {audio_duration:.2f}s + silence {silence_duration:.2f}s = target {target_duration:.2f}s")

    # 2. Collect segments until filling target_duration
    segments = []
    effective_video_duration = 0.0
    files_to_use = associated_video_files.copy()
    random.shuffle(files_to_use)
    max_segment_picking_attempts = len(files_to_use) * 3 + 5
    current_attempt_idx = 0
    file_picker_idx = 0

    while effective_video_duration < target_duration and current_attempt_idx < max_segment_picking_attempts:
        current_attempt_idx += 1
        if not files_to_use: break

        video_path = files_to_use[file_picker_idx % len(files_to_use)]
        source_video_duration = get_duration(video_path) or 0.0
        needed_effective_contribution = target_duration - effective_video_duration
        if needed_effective_contribution <= 0.01: break

        segment_raw_duration = 0.0
        is_first_segment = not bool(segments)
        min_raw_len_this_segment = MIN_SEGMENT_DURATION
        max_raw_len_this_segment = MAX_SEGMENT_DURATION

        if is_first_segment:
            ideal_len = min(needed_effective_contribution, max_raw_len_this_segment)
            segment_raw_duration = max(ideal_len, min_raw_len_this_segment if ideal_len >= min_raw_len_this_segment else ideal_len)
            segment_raw_duration = min(segment_raw_duration, source_video_duration)
        else:
            min_raw_len_this_segment = max(MIN_SEGMENT_DURATION, TRANSITION_DURATION + 0.01)
            target_raw_len_for_segment = needed_effective_contribution + TRANSITION_DURATION
            ideal_len = min(target_raw_len_for_segment, max_raw_len_this_segment)
            segment_raw_duration = max(ideal_len, min_raw_len_this_segment if ideal_len >= min_raw_len_this_segment else ideal_len)
            segment_raw_duration = min(segment_raw_duration, source_video_duration)

        valid_segment = True
        if segment_raw_duration < 0.1: valid_segment = False
        if not is_first_segment and segment_raw_duration <= TRANSITION_DURATION: valid_segment = False
        
        if not valid_segment:
            print(f"  Skipping {os.path.basename(video_path)} for {section_name}: calculated raw_t ({segment_raw_duration:.2f}s) unsuitable. Source_t: {source_video_duration:.2f}s.")
            file_picker_idx += 1
            continue

        start_time = random.uniform(0, max(0, source_video_duration - segment_raw_duration))
        print(f"  Segment for {section_name} from {os.path.basename(video_path)}: ss={start_time:.2f}, raw_t={segment_raw_duration:.2f}s")
        inp = ffmpeg.input(video_path, ss=start_time, t=segment_raw_duration)
        vid_node = apply_segment_effects(inp.video)
        segments.append({'stream': vid_node, 'raw_duration': segment_raw_duration})

        if is_first_segment:
            effective_video_duration += segment_raw_duration
        else:
            effective_video_duration += segment_raw_duration - TRANSITION_DURATION
        file_picker_idx += 1

    if not segments:
        print(f"Error: No video segments collected for {section_name} ({audio_file_path}). Target: {target_duration:.2f}s, Effective Found: {effective_video_duration:.2f}s")
        return None
    print(f"  Collected {len(segments)} segments for {section_name}. Effective video length: {effective_video_duration:.2f}s (target {target_duration:.2f}s)")

    # 3. Concatenate video segments with crossfades
    merged_video_stream = segments[0]['stream']
    timeline = segments[0]['raw_duration'] 
    for i in range(1, len(segments)):
        next_segment_data = segments[i]
        xfade_offset = max(0, timeline - TRANSITION_DURATION) 
        print(f"    Applying xfade to {section_name}: transition={XFADE_TRANSITIONS[0]}, duration={TRANSITION_DURATION:.2f}s, offset={xfade_offset:.2f}s")
        merged_video_stream = ffmpeg.filter(
            [merged_video_stream, next_segment_data['stream']], 'xfade',
            transition=XFADE_TRANSITIONS[0], duration=TRANSITION_DURATION, offset=xfade_offset
        ).filter('setpts', 'PTS-STARTPTS')
        timeline += next_segment_data['raw_duration'] - TRANSITION_DURATION
    print(f"  Video duration for {section_name} after xfades (before CTA fade): {timeline:.2f}s")

    # Apply fade-to-black for CTA section video stream
    if section_key == 'CTA':
        print(f"  Applying fade-to-black at the end of CTA section video.")
        # timeline is the actual duration of the video content for the CTA section
        fade_start_time = max(0, timeline - TRANSITION_DURATION)
        actual_fade_duration = timeline - fade_start_time
        
        if actual_fade_duration > 0.01: # Only apply if meaningful duration
            merged_video_stream = merged_video_stream.filter(
                'fade', type='out',
                start_time=fade_start_time,
                duration=actual_fade_duration,
                color='black' 
            )
            print(f"    CTA fade-out applied: start_time={fade_start_time:.2f}s, duration={actual_fade_duration:.2f}s. Video will end black.")
        else:
            print(f"    CTA video content ({timeline:.2f}s) too short for effective fade-out. Skipping fade for {section_name}.")

    # 4. Build padded audio
    tts_input = ffmpeg.input(audio_file_path)
    silence_input = ffmpeg.input(
        'anullsrc=channel_layout=stereo:sample_rate=44100', format='lavfi', t=silence_duration
    )
    padded_audio = ffmpeg.filter([tts_input.audio, silence_input.audio], 'concat', n=2, v=0, a=1)

    # 5. Merge video & audio for the section
    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    try:
        out_node = ffmpeg.output(
            merged_video_stream, padded_audio, output_file_path,
            vcodec=VIDEO_CODEC, acodec=AUDIO_CODEC, audio_bitrate=AUDIO_BITRATE,
            crf=CRF, preset=PRESET_X264, movflags='+faststart',
        )
        print(f"  Writing section reel: {output_file_path} (target section duration: {target_duration:.2f}s)")
        ffmpeg.run(out_node, overwrite_output=True, quiet=False)
        print(f"Completed section: {output_file_path}")
        return output_file_path
    except ffmpeg.Error as e:
        print(f"Error writing section {output_file_path}: {e}")
        if e.stderr: print(f"FFmpeg stderr: {e.stderr.decode('utf8')}")
        return None
    except Exception as e_gen:
        print(f"General error during output for section {output_file_path}: {e_gen}")
        return None


def concatenate_sections(section_files, final_output):
    list_path = os.path.join(os.path.dirname(final_output), 'sections_to_concat.txt')
    with open(list_path, 'w') as f:
        for filepath in section_files:
            abs_filepath = os.path.abspath(filepath).replace('\\', '/')
            f.write(f"file '{abs_filepath}'\n")

    print(f"Concatenating {len(section_files)} sections into {final_output}")
    try:
        (
            ffmpeg
            .input(list_path, format='concat', safe=0)
            .output(
                final_output, vcodec=VIDEO_CODEC, acodec=AUDIO_CODEC,
                audio_bitrate=AUDIO_BITRATE, crf=CRF, preset=PRESET_X264,
                movflags='+faststart'
            )
            .run(overwrite_output=True, quiet=False)
        )
        print(f"Final reel created: {final_output}")
    except ffmpeg.Error as e:
        print(f"Error concatenating final reel: {e}")
        if e.stderr: print(f"FFmpeg stderr: {e.stderr.decode('utf8')}")
    except Exception as e_gen:
         print(f"General error during final concatenation: {e_gen}")







def main():
    os.makedirs(OUTPUT_DIR_BASE, exist_ok=True)
    if not os.path.isdir(BASE_VIDEOS_PATH):
        print(f"Error: Base videos path not found: {BASE_VIDEOS_PATH}")
        return

    scripts = [d for d in os.listdir(BASE_VIDEOS_PATH)
               if os.path.isdir(os.path.join(BASE_VIDEOS_PATH, d))]

    for script in scripts:
        base_script_path = os.path.join(BASE_VIDEOS_PATH, script)
        audio_dir = os.path.join(base_script_path, 'audio')
        visuals_root = os.path.join(base_script_path, 'visuals')
        output_script_root = os.path.join(OUTPUT_DIR_BASE, script)
        os.makedirs(output_script_root, exist_ok=True)

        if not os.path.isdir(audio_dir):
            print(f"Audio directory not found for script {script}: {audio_dir}. Skipping script.")
            continue
        print(f"\nProcessing Script folder: {script}")

        # Store paths to generated section reels, mapped by section key
        section_output_map = {} 
        
        # Process audio files to generate sections
        available_audio_files = sorted([f for f in os.listdir(audio_dir) 
                                     if f.lower().endswith(('.wav', '.mp3', '.m4a', '.aac'))])
        if not available_audio_files:
            print(f"No audio files found in {audio_dir} for script {script}. Skipping script.")
            continue

        for audio_file in available_audio_files:
            section_name_from_audio = os.path.splitext(audio_file)[0]
            section_key_from_audio = section_name_from_audio.upper() # For matching SECTION_ORDER

            vids_for_section = []
            section_visuals_folder = os.path.join(visuals_root, f'section_{section_name_from_audio}')
            
            potential_visual_sources = []
            if os.path.isdir(section_visuals_folder):
                potential_visual_sources.append(section_visuals_folder)
            if os.path.isdir(visuals_root):
                potential_visual_sources.append(visuals_root)

            for source_dir in potential_visual_sources:
                vids_for_section.extend([
                    os.path.join(source_dir, f)
                    for f in os.listdir(source_dir)
                    if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm'))
                ])
            vids_for_section = sorted(list(set(vids_for_section)))

            audio_path = os.path.join(audio_dir, audio_file)
            safe_section_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in section_name_from_audio)
            output_section_reel_path = os.path.join(output_script_root, f'reel_{safe_section_name}.mp4')
            
            # The create_reel_for_audio function internally derives section_key for CTA fade
            result_path = create_reel_for_audio(audio_path, vids_for_section, output_section_reel_path)
            if result_path:
                section_output_map[section_key_from_audio] = result_path
        
        # After processing all audio files for the current script, prepare ordered list for concatenation
        ordered_section_files_for_concat = []
        print(f"\nPreparing final reel for script '{script}' based on order: {SECTION_ORDER}")
        for section_key_in_order in SECTION_ORDER:
            if section_key_in_order in section_output_map:
                ordered_section_files_for_concat.append(section_output_map[section_key_in_order])
                print(f"  + Added section '{section_key_in_order}'")
            else:
                print(f"  - Warning: Reel for section '{section_key_in_order}' is missing for script '{script}'. It will be excluded.")

        if ordered_section_files_for_concat:
            if len(ordered_section_files_for_concat) < len(SECTION_ORDER):
                 print(f"Warning: Concatenating {len(ordered_section_files_for_concat)} available sections for '{script}' (some were missing).")
            
            final_out_safe_script_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in script)
            final_reel_output_path = os.path.join(output_script_root, f'{final_out_safe_script_name}_final_ordered_reel.mp4')
            concatenate_sections(ordered_section_files_for_concat, final_reel_output_path)
        elif not available_audio_files:
             # This case is handled earlier by skipping the script.
             pass
        else: # Some audio files were processed, but none matched the required sections or failed.
            print(f"No sections were successfully processed and matched the defined order for script '{script}'. Final ordered reel will not be generated.")


if __name__ == '__main__':
    main()