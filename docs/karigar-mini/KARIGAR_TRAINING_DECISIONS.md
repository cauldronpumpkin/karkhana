# Karigar-Mini Training Decisions

## Decision

- Model: Qwen3.5-9B-Instruct dense.
- Method: supervised fine-tuning with bf16 LoRA.
- First dataset size target: 1k to 3k high-quality episodes.
- First evaluation: Karigar-Worker-100.
- Local inference target: quantized GGUF on a 16GB VRAM machine.
- Training target: Unsloth, Colab, or rented GPU, not the local PC.
- Cloud models: teacher, critic, rescue worker, and dataset generator.

## Rationale

Qwen3.5-9B-Instruct dense is the right first target because Karigar-Mini needs real code and instruction-following ability while staying close to local deployment constraints. The worker must learn a specific operating pattern for Karkhana: inspect Graphify and repo context, understand project twins and local worker lifecycle, make narrow branch changes, verify, report, and escalate.

SFT with bf16 LoRA is the right first method because the immediate goal is behavioral shaping. LoRA keeps iteration cost low and avoids the risk of full fine-tuning before the dataset and benchmark stabilize.

## Why Not QLoRA By Default

QLoRA is useful when GPU memory is the limiting factor, but the first training run should prefer bf16 LoRA if the training environment supports it. That keeps the training setup simpler while the team is still testing dataset quality, schema shape, and benchmark usefulness.

## Why Not Full Fine-Tuning

Full fine-tuning is too expensive and too irreversible for the first dataset. The initial 1k to 3k episodes will evolve quickly as worker traces, cloud rescues, and critic labels improve.

## Why Not DPO Or RL Yet

DPO and RL need stable preference data, strong rejection criteria, and reliable paired comparisons. Karigar-Mini first needs clean SFT examples and a fixed evaluation suite that proves the basic worker loop.

## Acceptance Gate

Do not train until the seed format, QA checklist, generation prompts, and Karigar-Worker-100 benchmark produce consistent accepted examples. Candidate data from cloud models or Hermes should remain untrusted until validated.

