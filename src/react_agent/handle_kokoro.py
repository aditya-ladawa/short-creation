from typing import Optional
import soundfile as sf
from misaki import en, espeak
from kokoro_onnx import Kokoro
from pathlib import Path
from react_agent.structures import AudioMetadata

fallback = espeak.EspeakFallback(british=False)
g2p = en.G2P(trf=False, british=False, fallback=fallback)
kokoro = Kokoro(
    "/home/aditya-ladawa/Aditya/z_projects/short_creation/kokoro_files/kokoro.onnx", 
    "/home/aditya-ladawa/Aditya/z_projects/short_creation/kokoro_files/voices-v1.0.bin"
)
BASE_PATH = Path("/home/aditya-ladawa/Aditya/z_projects/short_creation/my_test_files")

def generate_tts(
    text: str,
    video_name: str,
    section: str,
    voice: str = "af_heart",
    base_path: Path = BASE_PATH,
) -> Optional[AudioMetadata]:
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