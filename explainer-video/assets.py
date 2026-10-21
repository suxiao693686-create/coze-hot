"""第一次运行时下载乐器采样到 .cache/audio（只下载一次）。

- 钢琴：Salamander Grand Piano V3（Alexander Holm，CC BY 3.0），约 6MB
- 鼓和音效：Sonic Pi 采样库（CC0 公有领域），约 35MB

都从 npm 仓库下载压缩包（不需要装 npm），国外源连不上会自动换国内镜像。
"""

import io
import subprocess
import tarfile
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache" / "audio"
SR = 44100
PKGS = {
    "piano": ("@audio-samples/piano-mp3-velocity8", "1.0.5", "package/audio/"),
    "sonic": ("supersonic-scsynth-samples", "0.91.0", "package/samples/"),
}
REGISTRIES = ["https://registry.npmjs.org", "https://registry.npmmirror.com"]


def ensure(name):
    """返回采样目录；没有就下载"""
    pkg, ver, prefix = PKGS[name]
    out = CACHE / name
    if out.exists() and any(out.iterdir()):
        return out
    out.mkdir(parents=True, exist_ok=True)
    base = pkg.split("/")[-1]
    err = None
    for reg in REGISTRIES:
        url = f"{reg}/{pkg}/-/{base}-{ver}.tgz"
        try:
            print(f"  下载乐器采样 {name}（只需一次）…")
            data = urllib.request.urlopen(url, timeout=180).read()
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                for m in tf.getmembers():
                    if not m.isfile() or not m.name.startswith(prefix):
                        continue
                    fn = Path(m.name).name
                    if "/" in m.name[len(prefix):] or fn.startswith("."):
                        continue
                    (out / fn).write_bytes(tf.extractfile(m).read())
            return out
        except Exception as e:
            err = e
    raise RuntimeError(f"乐器采样下载失败：{err}")


_mem = {}


def load(name, file, mono=False):
    """解码一个采样为 float32，形状 (2, n)（mono=True 时为 (n,)），带硬盘缓存"""
    key = (name, file, mono)
    if key in _mem:
        return _mem[key]
    d = ensure(name)
    npy = d / f"{file}.{'m' if mono else 's'}.npy"
    if npy.exists():
        x = np.load(npy)
    else:
        src = next(p for p in d.iterdir() if p.stem == file or p.name == file)
        ch = 1 if mono else 2
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(src), "-f", "f32le", "-ac", str(ch), "-ar", str(SR), "-"],
            check=True, capture_output=True,
        ).stdout
        x = np.frombuffer(raw, np.float32).copy()
        x = x if mono else x.reshape(-1, 2).T.copy()
        # 去掉 mp3 编码带来的开头静音
        lvl = np.abs(x) if mono else np.abs(x).max(0)
        idx = np.where(lvl > 0.003)[0]
        if len(idx):
            x = x[idx[0]:] if mono else x[:, idx[0]:]
        np.save(npy, x)
    _mem[key] = x
    return x
