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
from transformers import UMT5EncoderModel  # noqa: E402

# Kaggle gives two 15 GB T4s: the text encoder (UMT5-XXL, about 11 GB) runs once on GPU 1, then leaves;
# the 5B video model and the VAE live on GPU 0. T5 overflows in fp16, so the encoder runs in bf16.
two = torch.cuda.device_count() > 1
t0 = time.time()
mid = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
te = UMT5EncoderModel.from_pretrained(mid, subfolder="text_encoder", torch_dtype=torch.bfloat16)
vae = AutoencoderKLWan.from_pretrained(mid, subfolder="vae", torch_dtype=torch.float32)
pipe = WanImageToVideoPipeline.from_pretrained(mid, vae=vae, text_encoder=te, torch_dtype=torch.float16)
print(f"loaded in {time.time() - t0:.0f}s, gpus={torch.cuda.device_count()}", flush=True)

neg = "blurry, low quality, distorted face, extra limbs, text, watermark, flicker"
enc_dev = "cuda:1" if two else "cpu"
pipe.text_encoder.to(enc_dev)
with torch.no_grad():
    pe, ne = pipe.encode_prompt(prompt=PROMPT, negative_prompt=neg, do_classifier_free_guidance=True,
                                num_videos_per_prompt=1, device=torch.device(enc_dev))
pe, ne = pe.to("cuda:0", torch.float16), ne.to("cuda:0", torch.float16)
pipe.text_encoder.to("cpu")
pipe.text_encoder = None
del te
torch.cuda.empty_cache()
pipe.transformer.to("cuda:0")
pipe.vae.to("cuda:0")
try:
    pipe.vae.enable_tiling()
except Exception:  # noqa: BLE001
    pass
print(f"prompt encoded; vram {torch.cuda.memory_allocated(0) / 1e9:.1f} GB", flush=True)

img = load_image(IMAGE_URL).convert("RGB")
# keep aspect; both sides multiples of 32, about 480p
w0, h0 = img.size
scale = (480 * 832 / (w0 * h0)) ** 0.5
w, h = int(w0 * scale) // 32 * 32, int(h0 * scale) // 32 * 32
img = img.resize((w, h))
t1 = time.time()
out = pipe(image=img, prompt_embeds=pe, negative_prompt_embeds=ne, height=h, width=w, num_frames=FRAMES,
           num_inference_steps=STEPS, guidance_scale=5.0).frames[0]
print(f"generated {len(out)} frames {w}x{h} in {time.time() - t1:.0f}s", flush=True)
export_to_video(out, f"{W}/clip.mp4", fps=24)
print("done", flush=True)
