# -*- coding: utf-8 -*-
"""Mascot voice "Mixi": Piper TTS (German multi-speaker model) + Praat "Change Gender" (parselmouth).

Cute small characters: higher pitch AND higher formants (a smaller "head"), livelier melody – pitch shifting with formant
correction would keep the adult vocal tract. Raw phonemes for English words: [[ ... ]] in the text."""
import io, os, wave
import numpy as np
import parselmouth
from parselmouth.praat import call
from piper import PiperVoice, SynthesisConfig

HERE = os.path.dirname(os.path.abspath(__file__))
PRESETS = {   # base voice file, speaker, formant shift ratio, new pitch median (Hz), pitch range factor, duration factor
    # "Mixi": Thorsten (clearest German Piper voice) with a smaller head (+22 % formants), ~260 Hz and a livelier melody
    "thorsten_klein": dict(model="de_DE-thorsten-high", speaker=None, formant=1.22, pitch=260, prange=1.5, duration=0.95),
}
_VOICES = {}

def _voice(model):
    if model not in _VOICES: _VOICES[model] = PiperVoice.load(os.path.join(HERE, model + ".onnx"))
    return _VOICES[model]

def speak(text, preset="thorsten_klein", sr_out=44100):
    """Returns (mono float32 at sr_out). Silence at the ends is trimmed."""
    p = PRESETS[preset]; v = _voice(p["model"]); buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        v.synthesize_wav(text, wf, syn_config=SynthesisConfig(speaker_id=p["speaker"]))
    buf.seek(0)
    with wave.open(buf) as wf: sr = wf.getframerate(); x = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float64)/32768
    snd = parselmouth.Sound(x, sampling_frequency=sr)
    snd = call(snd, "Change gender", 75, 600, p["formant"], p["pitch"], p["prange"], p["duration"])
    snd = call(snd, "Resample", sr_out, 50)
    y = snd.values[0]
    # a touch of presence and air, gentle level
    from scipy import signal
    sos = signal.butter(1, 3500, "highpass", fs=sr_out, output="sos"); y = y+0.25*signal.sosfilt(sos, y)
    nz = np.where(np.abs(y) > 0.01*np.max(np.abs(y)))[0]
    if len(nz): y = y[max(0, nz[0]-int(0.03*sr_out)):nz[-1]+int(0.08*sr_out)]
    return (y/max(1e-9, np.max(np.abs(y)))*0.89).astype(np.float32)

if __name__ == "__main__":
    import soundfile as sf, sys
    out = sys.argv[1] if len(sys.argv) > 1 else HERE
    txt = "Hallo! Ich bin Mixi, dein kleiner Klangschmied. Ich zeige dir in drei Minuten, wie [[ mˈɪkssmɪs ]] deine Songs mischt und mastert. Los geht's!"
    import time
    for k in PRESETS:
        t = time.time(); y = speak(txt, k); d = len(y)/44100
        sf.write(os.path.join(out, "Mixi_%s.wav" % k), y, 44100)
        print("%-15s %.1f s Audio (%.0f ms je Zeichen, normal 55-80)  %.1f s Rechenzeit" % (k, d, 1000*d/len(txt), time.time()-t), flush=True)
