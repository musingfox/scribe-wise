import numpy as np
import torch
import torchaudio
from transformers import WhisperForConditionalGeneration, WhisperProcessor


def transcribe_long_audio(audio_path, chunk_length_sec=30):
    # 1. Load audio
    waveform, sample_rate = torchaudio.load(audio_path)

    # 2. Preprocess
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0)
    waveform = waveform.squeeze()

    if sample_rate != 16_000:
        resampler = torchaudio.transforms.Resample(sample_rate, 16_000)
        waveform = resampler(waveform)
        sample_rate = 16_000

    # Use MPS if available (Apple Silicon), otherwise CPU
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Using device: {device}")

    # 3. Load Model
    processor = WhisperProcessor.from_pretrained("MediaTek-Research/Breeze-ASR-25")
    model = (
        WhisperForConditionalGeneration.from_pretrained(
            "MediaTek-Research/Breeze-ASR-25"
        )
        .to(device)
        .eval()
    )

    # 4. Split audio into chunks
    total_length = waveform.shape[0]
    chunk_samples = chunk_length_sec * sample_rate
    num_chunks = int(np.ceil(total_length / chunk_samples))

    duration_minutes = total_length / sample_rate / 60
    print(f"Audio duration: {duration_minutes:.1f} minutes")
    print(f"Processing in {num_chunks} segments, {chunk_length_sec} seconds each")

    transcriptions = []

    # 5. Process each chunk
    for i in range(num_chunks):
        start_idx = i * chunk_samples
        end_idx = min((i + 1) * chunk_samples, total_length)
        chunk = waveform[start_idx:end_idx]

        print(
            f"Processing segment {i + 1}/{num_chunks} ({start_idx / sample_rate:.1f}s - {end_idx / sample_rate:.1f}s)"
        )

        # Process chunk
        input_features = processor(
            chunk, sampling_rate=sample_rate, return_tensors="pt"
        ).input_features.to(device)

        # Generate transcription for this chunk
        with torch.no_grad():
            predicted_ids = model.generate(
                input_features,
                max_length=448,  # Allow longer sequences
                num_beams=1,  # Faster generation
                do_sample=False,  # Deterministic output
            )
            chunk_transcription = processor.batch_decode(
                predicted_ids, skip_special_tokens=True
            )[0]

        if chunk_transcription.strip():  # Only add non-empty transcriptions
            transcriptions.append(chunk_transcription.strip())
            print(f"Segment {i + 1} result: {chunk_transcription[:50]}...")

    # 6. Combine all transcriptions
    full_transcription = " ".join(transcriptions)
    return full_transcription


# Run transcription
audio_path = "meeting.mp3"
print("Starting long audio transcription...")
result_text = transcribe_long_audio(audio_path)

print(f"\nComplete transcription result ({len(result_text)} characters):")
print("=" * 50)
print(result_text)
print("=" * 50)

# Save transcription to file
with open("transcription.txt", "w", encoding="utf-8") as f:
    f.write(result_text)
print("\nTranscription saved to transcription.txt")
