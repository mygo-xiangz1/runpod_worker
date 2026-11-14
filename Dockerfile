# =====================================================================
# Undress Agent — RunPod Serverless ComfyUI worker
# base: official worker-comfyui 5.10.0 (clean, no models; models live
#       on the network volume under models/)
# build: RunPod GitHub integration (auto-build, max 30 min — this file
#        installs only code, no model downloads, so it is fast)
# =====================================================================
FROM runpod/worker-comfyui:5.10.0-base

# ---------------------------------------------------------------
# 1) Upgrade the bundled ComfyUI 0.34.0 -> v0.39.1.
#    The production graph uses QwenImage21Cache / TextEncodeQwenImage21,
#    which first exist in ComfyUI >= 0.39.
#    Then mirror the new requirements into the LAUNCH venv (/opt/venv),
#    same flags comfy-cli itself uses (see worker DR-1170 note).
# ---------------------------------------------------------------
RUN cd /comfyui \
    && git fetch --depth 1 origin tag v0.39.1 \
    && git checkout v0.39.1 \
    && uv pip install -r /comfyui/requirements.txt --python /opt/venv/bin/python \
         --index-strategy unsafe-best-match --prerelease=if-necessary-or-explicit

# ---------------------------------------------------------------
# 2) Custom nodes:
#    - comfyui_nvidia_rtx_nodes  -> RTXVideoSuperResolution (2x ULTRA)
#      (Comfy-Org official; pulls the `nvidia-vfx` pip package)
#    - UnetLoaderGGUF: the registry slug `comfyui-gguf` installs a
#      different package that does NOT provide this class, so vendor
#      city96/ComfyUI-GGUF from source instead (same copy as local).
# ---------------------------------------------------------------
RUN comfy-node-install comfyui_nvidia_rtx_nodes
RUN /opt/venv/bin/python -m pip install --no-cache-dir 'gguf>=0.13.0' sentencepiece protobuf \
    && ( [ -x /comfyui/.venv/bin/python ] \
         && /comfyui/.venv/bin/python -m pip install --no-cache-dir 'gguf>=0.13.0' sentencepiece protobuf \
         || true )
COPY custom_nodes/ComfyUI-GGUF /comfyui/custom_nodes/ComfyUI-GGUF

# ---------------------------------------------------------------
# 3) Belt & braces: start.sh launches ComfyUI with /opt/venv python,
#    so make sure nvidia-vfx (import `nvvfx`) is visible there too.
#    (plain pip — uv-only flags like --index-strategy don't apply here)
# ---------------------------------------------------------------
RUN /opt/venv/bin/python -m pip install --no-cache-dir nvidia-vfx \
    && ( [ -x /comfyui/.venv/bin/python ] \
         && /comfyui/.venv/bin/python -m pip install --no-cache-dir nvidia-vfx \
         || true )

# ---------------------------------------------------------------
# 4) ComfyUI-PhotoTexture -> LocalPhotoTextureAdjust.
#    Closed-source, not on the registry: vendored from the local
#    machine (pure torch, zero extra deps).
# ---------------------------------------------------------------
COPY custom_nodes/ComfyUI-PhotoTexture /comfyui/custom_nodes/ComfyUI-PhotoTexture

# ---------------------------------------------------------------
# 5) Smoke-test input image baked into ComfyUI's input dir so the
#    test workflow's LoadImage finds it with zero upload.
# ---------------------------------------------------------------
COPY test_input.png /comfyui/input/test_input.png

# No model downloads here: the network volume is mounted at
# /runpod-volume and the worker maps /runpod-volume/models/* into
# ComfyUI at startup (qwen-image-2.1-UC-Q6_K.gguf, qwen3vl_8b_int8_convrot,
# qwen_image_2.1_vae_bf16, 4x loras).
