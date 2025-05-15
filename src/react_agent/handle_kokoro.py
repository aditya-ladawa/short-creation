import os
from pathlib import Path
from typing import Optional

import soundfile as sf
from dotenv import load_dotenv
from kokoro_onnx import Kokoro
from misaki import en, espeak
from react_agent.structures import AudioMetadata

load_dotenv()


fallback = espeak.EspeakFallback(british=False)
g2p = en.G2P(trf=False, british=False, fallback=fallback)
kokoro = Kokoro(
    os.environ.get('KOKORO_MODEL_PATH'), 
    os.environ.get('KOKORO_VOICES_PATH')
)
BASE_PATH = Path(os.environ.get('BASE_PATH'))

def generate_tts(
    text: str,
    video_name: str,
    section: str,
    voice: str = "af_jessica",
    base_path: Path = BASE_PATH) -> Optional[AudioMetadata]:
    """Generates TTS audio with proper error handling"""



    try:
        
        audio_dir = base_path / "videos" / video_name / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        file_path = audio_dir / f"{section.replace(" ", '_')}.wav"
        print(file_path)

        phonemes, _ = g2p(text)
        samples, sample_rate = kokoro.create(phonemes, voice, is_phonemes=True)
        
        sf.write(file_path, samples, sample_rate)
        
        return AudioMetadata(
            section=section,
            text=text,
            voice=voice,
            duration=len(samples)/sample_rate,
            sample_rate=sample_rate,
            file_path=str(file_path.absolute())
        )
    
    except Exception as e:
        print(f"❌ TTS Generation Failed for {section}: {str(e)}")
    return None