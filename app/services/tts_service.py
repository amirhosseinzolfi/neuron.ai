import mimetypes
import struct
from pathlib import Path
from typing import List
from google import genai
import os
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
DEFAULT_VOICE = "zephyr"
VOICE_API_KEYS = [
    "GOOGLE_API_KEY_VOICE",
    "GOOGLE_API_KEY_VOICE2",
    "GOOGLE_API_KEY_VOICE3",
]


class TTSService:
    def __init__(self):
        self.api_keys = [
            os.getenv(key_name)
            for key_name in VOICE_API_KEYS
            if os.getenv(key_name)
        ]
        if not self.api_keys:
            raise ValueError("No valid Google API key found for TTS service")
        self.client = genai.Client(api_key=self.api_keys[0])
        self.output_dir = Path("tools/voice")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        text: str,
        model: str = "gemini-2.5-flash-preview-tts",
        output_format: str = "wav",
        voice: str = None,
    ) -> List[Path]:
        """Generate speech from text."""
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=text)])]
        
        # Use provided voice or default
        voice_name = voice if voice else DEFAULT_VOICE
        
        config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
        
        last_error = None
        for index, api_key in enumerate(self.api_keys):
            try:
                client = genai.Client(api_key=api_key)
                saved_files = self._stream_generate(
                    client, model, contents, config, output_format
                )
                if saved_files:
                    self.client = client
                    return saved_files
                last_error = RuntimeError(
                    "No audio generated using Google API key"
                )
            except Exception as exc:  # noqa: PERF203
                last_error = exc
        raise RuntimeError(
            "Unable to generate speech with any configured Google API key"
        ) from last_error

    def _stream_generate(
        self,
        client,
        model,
        contents,
        config,
        output_format,
    ) -> List[Path]:
        saved_files = []
        file_index = 0

        for chunk in client.models.generate_content_stream(
            model=model, contents=contents, config=config
        ):
            if not (chunk.candidates and chunk.candidates[0].content and 
                    chunk.candidates[0].content.parts):
                continue

            inline_data = chunk.candidates[0].content.parts[0].inline_data
            if inline_data and inline_data.data:
                data = inline_data.data
                ext = mimetypes.guess_extension(inline_data.mime_type) or ".wav"

                if ext == ".wav" or output_format == "wav":
                    data = self._convert_to_wav(data, inline_data.mime_type)
                    ext = ".wav"

                file_path = self.output_dir / f"generated_voice_{file_index}{ext}"
                file_path.write_bytes(data)
                saved_files.append(file_path)
                file_index += 1

        return saved_files

    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        """Convert audio data to WAV format."""
        params = self._parse_mime_type(mime_type)
        bits_per_sample = params["bits_per_sample"]
        sample_rate = params["rate"]
        data_size = len(audio_data)
        
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE", b"fmt ", 16, 1, 1,
            sample_rate, sample_rate * (bits_per_sample // 8),
            bits_per_sample // 8, bits_per_sample, b"data", data_size
        )
        return header + audio_data

    def _parse_mime_type(self, mime_type: str) -> dict:
        """Parse audio parameters from MIME type."""
        bits_per_sample, rate = 16, 24000
        for param in mime_type.split(";"):
            param = param.strip()
            if param.lower().startswith("rate="):
                try:
                    rate = int(param.split("=", 1)[1])
                except (ValueError, IndexError):
                    pass
            elif param.startswith("audio/L"):
                try:
                    bits_per_sample = int(param.split("L", 1)[1])
                except (ValueError, IndexError):
                    pass
        return {"bits_per_sample": bits_per_sample, "rate": rate}

