"""Image-to-video on a Kaggle GPU with Wan 2.2 TI2V-5B (Apache 2.0), pushed by .github/workflows/ai-kaggle.yml.

Turns one still (a persona sheet shot, a Blender frame, an Antigravity plate) into a short motion clip.
IMAGE_URL, PROMPT, FRAMES, STEPS are filled in by the workflow. Output: /kaggle/working/clip.mp4.
No secrets live here. Disclose AI in every upload that uses these clips.
"""
import os
import subprocess
import sys
import time

IMAGE_URL = "__IMAGE_URL__"
PROMPT = """__PROMPT__"""
FRAMES = int("__FRAMES__")      # 4k+1, e.g. 49 = 2 s at 24 fps
STEPS = int("__STEPS__")
W = "/kaggle/working"
os.environ.setdefault("HF_HOME", "/tmp/hf")


def sh(cmd):
    print("+", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)


sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
sh(f"{sys.executable} -m pip install -q -U 'diffusers>=0.35' transformers accelerate ftfy imageio imageio-ffmpeg sentencepiece")

import torch  # noqa: E402
from diffusers import AutoencoderKLWan, WanImageToVideoPipeline  # noqa: E402
from diffusers.utils import export_to_video, load_image  # noqa: E402

t0 = time.time()
mid = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
dtype = torch.float16  # T4 has no fast bf16
vae = AutoencoderKLWan.from_pretrained(mid, subfolder="vae", torch_dtype=torch.float32)
pipe = WanImageToVideoPipeline.from_pretrained(mid, vae=vae, torch_dtype=dtype)
pipe.enable_model_cpu_offload()
try:
    pipe.vae.enable_tiling()
except Exception:  # noqa: BLE001
    pass
print(f"loaded in {time.time() - t0:.0f}s", flush=True)

img = load_image(IMAGE_URL).convert("RGB")
# keep aspect; both sides multiples of 32, about 480p
w0, h0 = img.size
scale = (480 * 832 / (w0 * h0)) ** 0.5
w, h = int(w0 * scale) // 32 * 32, int(h0 * scale) // 32 * 32
img = img.resize((w, h))
neg = "blurry, low quality, distorted face, extra limbs, text, watermark, flicker"
t1 = time.time()
out = pipe(image=img, prompt=PROMPT, negative_prompt=neg, height=h, width=w, num_frames=FRAMES,
           num_inference_steps=STEPS, guidance_scale=5.0).frames[0]
print(f"generated {len(out)} frames {w}x{h} in {time.time() - t1:.0f}s", flush=True)
export_to_video(out, f"{W}/clip.mp4", fps=24)
print("done", flush=True)
