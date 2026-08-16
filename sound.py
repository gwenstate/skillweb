import io
import wave
import threading
import numpy as np
import winsound

SAMPLE_RATE = 44100


def _to_wav_bytes(audio_int16):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()


def _generate_thwip():
    duration = 0.12
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    freq = np.linspace(1800, 300, len(t))
    wave_data = np.sin(2 * np.pi * freq * t)
    envelope = np.linspace(1, 0, len(t)) ** 1.5
    wave_data *= envelope
    audio = (wave_data * 32767 * 0.5).astype(np.int16)
    return _to_wav_bytes(audio)


def _generate_gunshot():
    duration = 0.15
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False)

    noise = np.random.uniform(-1, 1, n)
    noise_env = np.exp(-np.linspace(0, 14, n))

    thump = np.sin(2 * np.pi * 85 * t)
    thump_env = np.exp(-np.linspace(0, 9, n))

    wave_data = noise * noise_env * 0.6 + thump * thump_env * 0.7
    wave_data = np.clip(wave_data, -1, 1)
    audio = (wave_data * 32767 * 0.8).astype(np.int16)
    return _to_wav_bytes(audio)


def _generate_hit():
    duration = 0.16
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    wave_data = np.sin(2 * np.pi * 1200 * t) + 0.5 * np.sin(2 * np.pi * 2400 * t)
    envelope = np.exp(-np.linspace(0, 7, len(t)))
    wave_data *= envelope
    audio = (wave_data * 32767 * 0.45).astype(np.int16)
    return _to_wav_bytes(audio)


_THWIP = _generate_thwip()
_GUNSHOT = _generate_gunshot()
_HIT = _generate_hit()


def play_thwip():
    threading.Thread(target=lambda: winsound.PlaySound(_THWIP, winsound.SND_MEMORY), daemon=True).start()


def play_gunshot():
    threading.Thread(target=lambda: winsound.PlaySound(_GUNSHOT, winsound.SND_MEMORY), daemon=True).start()


def play_hit():
    threading.Thread(target=lambda: winsound.PlaySound(_HIT, winsound.SND_MEMORY), daemon=True).start()