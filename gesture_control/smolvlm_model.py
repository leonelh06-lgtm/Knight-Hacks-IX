"""Shared local SmolVLM2 inference for the video probe and live controls."""

import time

MODEL = 'HuggingFaceTB/SmolVLM2-256M-Video-Instruct'
REVISION = '9b299836fe84e0aabd39e1e07651e569e5dfe87c'
LABELS = ('open_palm', 'fist', 'index_pinch', 'pinkie_pinch', 'unknown')
PROMPT = (
    'Classify the visible hand. Reply with exactly one label and no explanation: '
    'open_palm, fist, index_pinch, pinkie_pinch, unknown. '
    'open_palm: fingers extended, palm facing camera. fist: fingers curled closed. '
    'index_pinch: thumb touching index fingertip, other fingers extended. '
    'pinkie_pinch: thumb touching little fingertip, other fingers extended. '
    'unknown: no clear hand, relaxed hand, ambiguous posture, or cannot tell. '
    'Distinguish which finger touches the thumb; do not guess when unclear.'
)


def parse_label(answer):
    candidate = answer.strip().lower().strip('`\"\' .\n')
    return candidate if candidate in LABELS else 'unknown'


class LocalModel:
    def __init__(self, device, offline, revision):
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
        self.torch = torch
        self.device = device
        if device == 'cuda' and not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable in this Python environment. Install a '
                               'JetPack-compatible CUDA PyTorch build, or explicitly use --device cpu.')
        self.dtype = torch.float16 if device == 'cuda' else torch.float32
        options = dict(revision=revision, local_files_only=offline, trust_remote_code=False)
        self.processor = AutoProcessor.from_pretrained(MODEL, **options)
        self.model = AutoModelForImageTextToText.from_pretrained(
            MODEL, torch_dtype=self.dtype, attn_implementation='eager',
            use_safetensors=True, **options).to(device).eval()

    def synchronize(self):
        if self.device == 'cuda':
            self.torch.cuda.synchronize()

    def predict(self, rgb):
        from PIL import Image
        messages = [{'role': 'user', 'content': [
            {'type': 'image', 'image': Image.fromarray(rgb)},
            {'type': 'text', 'text': PROMPT}]}]
        self.synchronize()
        started = time.perf_counter()
        inputs = self.processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True,
            return_dict=True, return_tensors='pt')
        inputs = {key: value.to(device=self.device, dtype=self.dtype)
                  if value.is_floating_point() else value.to(self.device)
                  for key, value in inputs.items()}
        with self.torch.inference_mode():
            output = self.model.generate(**inputs, do_sample=False, max_new_tokens=24)
        answer = self.processor.batch_decode(
            output[:, inputs['input_ids'].shape[1]:], skip_special_tokens=True)[0]
        self.synchronize()
        return answer, (time.perf_counter() - started) * 1000


