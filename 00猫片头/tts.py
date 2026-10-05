"""离线配音（Kokoro 中文模型）。用法: python3 tts.py "文字" 输出.wav [语速] [音色编号]"""
import os, sys, wave
import numpy as np
import sherpa_onnx

d = os.environ.get("TTS_MODEL", "kokoro-multi-lang-v1_1") + "/"
tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
    model=sherpa_onnx.OfflineTtsModelConfig(
        kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=d + "model.onnx", voices=d + "voices.bin", tokens=d + "tokens.txt",
            data_dir=d + "espeak-ng-data", dict_dir=d + "dict",
            lexicon=d + "lexicon-us-en.txt," + d + "lexicon-zh.txt"),
        num_threads=4),
    rule_fsts=f"{d}phone-zh.fst,{d}date-zh.fst,{d}number-zh.fst"))
text, out = sys.argv[1], sys.argv[2]
speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
sid = int(sys.argv[4]) if len(sys.argv) > 4 else 23  # 23 号：音调高、起伏大，听着最有精神
a = tts.generate(text, sid=sid, speed=speed)
x = np.array(a.samples, dtype=np.float32)
on = np.where(np.abs(x) > 0.02)[0]  # 去掉首尾静音
x = x[max(0, on[0] - 1500): on[-1] + 2000]
with wave.open(out, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(a.sample_rate)
    w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
print(out, round(len(x) / a.sample_rate, 2))
