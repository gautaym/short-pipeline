# Maya 2 Native text-to-speech (Apache 2.0) needs Linux; this image runs it on the GPU from Windows.
#   docker build -t maya-tts docker/maya
#   docker run -d --gpus all --name maya-tts -v D:/PROJECTS_G/reels:/work maya-tts
# The voice engine then calls `docker exec maya-tts python /work/ai/tts_maya.py <jobs>` (voices "maya:...").
FROM pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime
RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg gcc libc6-dev && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "maya3[server] @ git+https://github.com/MayaResearch/maya2-native" soundfile \
        --extra-index-url https://download.pytorch.org/whl/cu128 \
    # maya3 upgrades torch, which leaves the base image's torchvision mismatched; nothing here needs it
    && pip uninstall -y torchvision
ENV HF_HOME=/work/models/hf
WORKDIR /work
CMD ["sleep", "infinity"]
