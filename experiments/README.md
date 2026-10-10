# SmolVLM2 feasibility probe (experimental / throwaway)

Question: can Hugging Face's SmolVLM2 distinguish open palm, fist, index-thumb
pinch, and pinkie-thumb pinch with useful accuracy and latency on our Jetson?
This standalone probe samples individual images from a recorded video. It does
not change the game or validate exercise quality. Keep it experimental until
actual results support adding a feedback feature.

Model: [HuggingFaceTB/SmolVLM2-256M-Video-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM2-256M-Video-Instruct),
developed by Hugging Face, Apache 2.0. We pin a model revision for repeatability.
Local loading follows the [Transformers SmolVLM documentation](https://huggingface.co/docs/transformers/model_doc/smolvlm).
Inference uses local PyTorch, not a hosted inference API. First use downloads
model/processor files; `--offline` requires those files already cached.

## Jetson setup

Run these from the repository root on the Jetson, after pulling this code.
Use a separate environment so dependency experiments don't disturb the game:

```bash
python3 -m venv --system-site-packages .venv-smolvlm
source .venv-smolvlm/bin/activate
python -c "import torch; print(torch.__version__); print('CUDA:', torch.cuda.is_available())"
```

CUDA must print `True` for the default GPU test. MediaPipe GPU working does NOT
prove PyTorch CUDA is installed. If torch is missing or CUDA is False, use a
CUDA-enabled PyTorch package/container compatible with your **exact JetPack**
release; consult [NVIDIA's Jetson PyTorch setup](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html).
Do not blindly install generic `pip install torch` and assume Jetson GPU support.
`--system-site-packages` exposes an existing system PyTorch installation; it does
not install one. A container must also have this repository and video mounted.

Once CUDA is available:

```bash
python -m pip install -r experiments/requirements-smolvlm.txt
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
python experiments/smolvlm_probe.py --video recordings/hand-test.mp4
```

The probe uses FP16 on CUDA, FP32 on explicit `--device cpu`, and eager attention
to avoid requiring FlashAttention builds. CUDA failure does not fall back to CPU.
Model loading/download can take time; close the game for this first measurement.
Latency and available memory on our Jetson are not yet verified.

## Accuracy test

Make four separate clips, with the whole hand visible and palm toward the camera.
Hold ONE gesture throughout each clip; remove transitions from labeled clips.
Include several people and lighting conditions. Labels describe the gesture
actually visible, not the gesture the participant was instructed to perform.

```bash
python experiments/smolvlm_probe.py --video recordings/open.mp4 --expected open_palm --output benchmark-results/smolvlm-open.csv
python experiments/smolvlm_probe.py --video recordings/fist.mp4 --expected fist --output benchmark-results/smolvlm-fist.csv
python experiments/smolvlm_probe.py --video recordings/index.mp4 --expected index_pinch --output benchmark-results/smolvlm-index.csv
python experiments/smolvlm_probe.py --video recordings/pinkie.mp4 --expected pinkie_pinch --output benchmark-results/smolvlm-pinkie.csv
```

Also test no hand, relaxed/ambiguous hands, and simultaneous pinches with
`--expected unknown`. This checks whether the model guesses when it should abstain.
For a mixed-gesture clip, omit `--expected` and compare the timestamped predictions
to manual labels. No accuracy is reported without ground truth.

Default: at most 12 images, one every 2 seconds, one warmup inference excluded.
`--samples` and `--interval` change sampling. `--offline` prevents Hub downloads
after caching. Unrecognized generated answers become `unknown`; the full answer
is retained for inspection. The model is generative, not a validated gesture
classifier: it may confuse fingers or return explanations instead of labels.

CSV contains predictions, raw answers, latency, and optional agreement. JSON
contains the exact prompt, model revision, device, versions, and mean latency.
Timing includes preprocessing, generation and decoding with CUDA synchronization;
it excludes video decoding, download/loading, and warmup. This is not game FPS
or the MediaPipe inference benchmark, so don't compare their times as equivalent.
On failure a partial CSV may remain; a complete run prints `Results:` and exits 0.

Video-only check (does not load or test the AI):

```bash
python experiments/smolvlm_probe.py --video recordings/hand-test.mp4 --dry-run
```

To leave the probe environment: `deactivate`. Activate `.venv` to return to the game.
Decide on game integration only after reviewing gesture agreement, unknown cases,
latency, and resource use on the real Jetson. No model inference has been verified
on the team's Jetson by this probe's author yet.
