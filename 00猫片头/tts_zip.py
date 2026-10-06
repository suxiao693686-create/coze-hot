"""00猫配音（ZipVoice，更像真人口播）。
按 voice/00猫声音模板.wav 的语气和音色来念；每句生成几遍，用语音识别挑念得最准的一遍。
用法: python3 tts_zip.py "文字" 输出.wav [语速=1.0] [生成几遍=3]
需要的模型（build.sh 会自动下载）放在 $MODELS 目录下：
  sherpa-onnx-zipvoice-distill-int8-zh-en-emilia/  vocos_24khz.onnx  sherpa-onnx-paraformer-zh-small-2024-03-09/
"""
import difflib, os, re, sys, wave
import numpy as np
import sherpa_onnx

HERE = os.path.dirname(os.path.abspath(__file__))
M = os.environ.get("MODELS", os.path.join(HERE, "build")) + "/"
REF_WAV = os.path.join(HERE, "voice", "00猫声音模板.wav")
REF_TEXT = "好家伙！你猜怎么着？我跟你说，这事儿可太有意思了，今天咱就来好好唠一唠！"

Z = M + "sherpa-onnx-zipvoice-distill-int8-zh-en-emilia/"
tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
    zipvoice=sherpa_onnx.OfflineTtsZipvoiceModelConfig(
        tokens=Z + "tokens.txt", encoder=Z + "encoder.int8.onnx", decoder=Z + "decoder.int8.onnx",
        data_dir=Z + "espeak-ng-data", lexicon=Z + "lexicon.txt", vocoder=M + "vocos_24khz.onnx"),
    num_threads=4)))
A = M + "sherpa-onnx-paraformer-zh-small-2024-03-09/"
asr = sherpa_onnx.OfflineRecognizer.from_paraformer(paraformer=A + "model.int8.onnx", tokens=A + "tokens.txt", num_threads=4)

with wave.open(REF_WAV) as w:
    ref = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    ref_sr = w.getframerate()

def norm(s):
    return re.sub(r"[^\w]", "", s.lower().replace("-", ""))

def say(text, speed):
    g = sherpa_onnx.GenerationConfig()
    g.reference_audio, g.reference_sample_rate, g.reference_text = ref, ref_sr, REF_TEXT
    g.num_steps, g.speed = 4, speed
    g.extra["min_char_in_sentence"] = "30"
    a = tts.generate(text, g)
    return np.array(a.samples, dtype=np.float32), a.sample_rate

def score(x, sr, text):
    s = asr.create_stream(); s.accept_waveform(sr, x); asr.decode_stream(s)
    return difflib.SequenceMatcher(None, norm(s.result.text), norm(text)).ratio(), s.result.text

text, out = sys.argv[1], sys.argv[2]
speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
tries = int(sys.argv[4]) if len(sys.argv) > 4 else 3
best = None
for _ in range(tries):
    x, sr = say(text, speed)
    sc, heard = score(x, sr, text)
    if best is None or sc > best[0]: best = (sc, heard, x, sr)
    if sc > 0.97: break
sc, heard, x, sr = best
on = np.where(np.abs(x) > 0.02)[0]
x = x[max(0, on[0] - 1500): on[-1] + 2400]          # 去掉首尾静音
with wave.open(out, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
print(f"{out}\t{len(x) / sr:.2f}s\t准确度{sc:.2f}\t{heard}")
