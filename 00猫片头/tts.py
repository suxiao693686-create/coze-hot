import sys, sherpa_onnx, wave, numpy as np
import os
d = os.environ.get("TTS_MODEL", "vits-melo-tts-zh_en") + "/"
cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
    vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=d+"model.onnx", lexicon=d+"lexicon.txt", tokens=d+"tokens.txt", dict_dir=d+"dict"),
    num_threads=4), rule_fsts=f"{d}phone.fst,{d}date.fst,{d}number.fst")
tts = sherpa_onnx.OfflineTts(cfg)
text, out, speed = sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv)>3 else 1.0
a = tts.generate(text, sid=0, speed=speed)
s = np.clip(np.array(a.samples)*32767, -32768, 32767).astype(np.int16)
with wave.open(out, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(a.sample_rate); w.writeframes(s.tobytes())
print(a.sample_rate, len(s)/a.sample_rate)
