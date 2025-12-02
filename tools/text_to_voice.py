import argparse
import mimetypes
import os
import struct
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

SAMPLE_TEXT = (
    "Read aloud in a warm, welcoming tone.\n"
    "Speaker 1: Welcome to the Blue Psychology text to voice demo.\n"
    "Speaker 2: This script converts your prompt into natural speech using Gemini TTS."
)

def save_binary_file(file_path: Path, data: bytes) -> None:
    """Writes audio data to disk, ensuring the folder exists."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "wb") as handle:
        handle.write(data)
    print(f"File saved to: {file_path}")

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    """Parses bits per sample and rate from an audio MIME type string."""
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}

def text_to_voice(
    text: str,
    output_filename: str = "output_voice",
    output_dir: str | os.PathLike[str] = "voice",
    model: str = "gemini-2.5-flash-preview-tts",
) -> list[Path]:
    """Converts text to voice using Gemini AI and writes audio files under ``output_dir``."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")

    client = genai.Client(api_key=api_key)
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=text),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["audio"],
    )

    output_path = Path(output_dir)
    saved_files: list[Path] = []
    file_index = 0
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if (
            chunk.candidates is None
            or chunk.candidates[0].content is None
            or chunk.candidates[0].content.parts is None
        ):
            continue
        if chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data:
            inline_data = chunk.candidates[0].content.parts[0].inline_data
            data_buffer = inline_data.data
            file_extension = mimetypes.guess_extension(inline_data.mime_type)
            if file_extension is None:
                file_extension = ".wav"
                data_buffer = convert_to_wav(inline_data.data, inline_data.mime_type)
            file_path = output_path / f"{output_filename}_{file_index}{file_extension}"
            file_index += 1
            save_binary_file(file_path, data_buffer)
            saved_files.append(file_path)
        else:
            print(chunk.text)

    return saved_files

if __name__ == "__main__":
    input_text = """


خداوند در این آیه می‌فرماید که امانت (که مفسران آن را عقل، اختیار، مسئولیت یا عشق الهی دانسته‌اند) را بر آسمان‌ها و زمین و کوه‌ها عرضه کردیم، اما آنها نپذیرفتند؛ انسان آن را پذیرفت.

در نتیجه:

حافظ می‌گوید آسمان با همه عظمتش تاب این بار نداشت،

و «قرعه» یعنی تقدیر و انتخاب، به نام او (انسان یا شاعر) افتاد،

آن هم دیوانه‌وار، یعنی با بی‌پروايی و عشق و شور، نه با عقل حسابگر.



---

🔹 معنی باطنی و عرفانی

در سطح عرفانی، «امانت» اشاره دارد به عشق الهی، آگاهی و مسئولیت انسان در برابر هستی.

1. آسمان در اینجا نماد عقل و نظم کیهانی است؛
یعنی موجودی که از دید عرفا، محدود و حسابگر است و توان پذیرش بی‌نظمی و شور عشق را ندارد.


2. انسان دیوانه نماد عاشق عارف است،
که با همه خطرها، دل به عشق سپرده و «آتش عشق» را برگزیده است.


3. بنابراین حافظ با نوعی طنز لطیف و تلخ می‌گوید:
«آسمان خرد و حسابگری نتوانست این عشق را بکشد، این دیوانگی را من بر دوش کشیدم.»




---

🔹 تفسیر روان‌شناختی و فلسفی

از دید روان‌شناختی:

"آسمان" می‌تواند نماد نظم، قانون و محدودیت عقل باشد.

"دیوانگی" نماد ناخودآگاه، شهود، احساس، و جرأت پذیرش رنج آگاهی است.


انسان در مقام موجودی آگاه، بار مسئولیتِ دانستن، انتخاب کردن و رنج کشیدن را پذیرفته است — در حالی که جهان طبیعت از این رنج رهاست.
به تعبیر امروزی، حافظ می‌گوید:

> «منِ انسان، مسئولیت آگاهی را پذیرفتم، گرچه این آگاهی دردناک است.»




---

🔹 نگاه عاشقانه

در مسیر عشق نیز همین معنا برقرار است:

عشق بار سنگینی است که عقل (آسمان) از کشیدنش عاجز است.

اما دل عاشق (دیوانه) با بی‌پروايی می‌گوید:
"من این بار را بر دوش می‌کشم، حتی اگر بسوزم."

---

🔹 جمع‌بندی نهایی

واژه	نماد	معنا

آسمان	عقل، نظم، حسابگری	ناتوان از درک و تحمل عشق
امانت	عشق الهی، آگاهی، مسئولیت انسانی	سنگین و الهی
دیوانه	انسانِ عاشق و عارف	جسور در برابر عقل
قرعه	تقدیر و انتخاب ازلی	نقش خاص انسان در هستی


📜 نتیجه:
این بیت بیان‌گر سرنوشت انسان است؛ موجودی که با دیوانگیِ عشق، مسئولیت آگاهی را پذیرفت و از این رو، برتر از آسمان شد — اما در عین حال، رنج‌کش و تنهاترین موجود عالم نیز گشت.
"""
    text_to_voice(input_text, "generated_voice")
