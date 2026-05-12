# Karigar-Mini Dataset Strategy

Karigar-Mini is a local coding-worker model for Karkhana-shaped tasks in Idea Refinery. It is not meant to be a broad chat assistant or a replacement for the cloud planning layer. Its job is to operate as a narrow local worker that can inspect a repository, understand a work item, make a small feature-branch change, run targeted verification, report honestly, and escalate when the task is too ambiguous, unsafe, or outside local capability.

## First Model Choice

The first target should be Qwen3.5-9B-Instruct dense because the worker needs stronger instruction following and code reasoning than a tiny model can provide, while still staying close to local deployment reality. A 9B dense model is large enough to learn Karkhana-specific habits such as project twin inspection, local worker job lifecycle reasoning, Graphify-first navigation, FastAPI/Svelte slice changes, and final worker reporting. After training, the local inference target is a quantized GGUF suitable for a 16GB VRAM machine.

## Training Method

Start with supervised fine-tuning using bf16 LoRA.

Use SFT because the first problem is behavioral imitation: teach the worker the Karkhana loop of inspect, plan, edit narrowly, verify, summarize, and escalate. Use LoRA because it is cheaper, easier to iterate, and safer than full fine-tuning. Use bf16 because the training target is rented GPU, Colab, or Unsloth-style infrastructure, not a local consumer PC.

Do not start with full fine-tuning. The first dataset will be small and evolving, and full fine-tuning would increase cost and risk without enough evidence that the target behavior is stable.

Do not start with DPO or RL. Preference optimization needs reliable paired judgments and stable failure taxonomies. Karigar-Mini first needs clean single-trajectory examples and a fixed benchmark.

Do not default to QLoRA for the first run unless GPU memory forces it. QLoRA is useful for memory pressure, but bf16 LoRA keeps the first training path simpler and avoids quantization-related training noise while the dataset itself is still being proven.

## Worker Role

Karigar-Mini should learn to:

- Read Graphify context before broad repo exploration.
- Inspect relevant backend, frontend, worker, script, and test surfaces.
- Respect project twins, work items, agent runs, local workers, build handoff, memory, commits, and Graphify as Karkhana control-plane concepts.
- Make narrow feature-branch changes only when asked to implement.
- Avoid touching runtime behavior during research, planning, dataset, or audit tasks.
- Run targeted checks and report exact validation.
- Preserve unrelated user changes.
- Escalate to cloud rescue when blocked by ambiguous requirements, unsafe credentials, missing runtime state, failing local services, or architectural risk.

## Worker Non-Goals

Karigar-Mini must not:

- Deploy to real AWS or use real cloud profiles for local Floci work.
- Add auth bypasses such as `AUTH_DISABLED` or `SKIP_AUTH`.
- Rewrite god-node services casually.
- Modify `worker-app/src-tauri/src/config.rs` unless the task explicitly requires it and the change is reviewed.
- Invent test results, files, routes, or command output.
- Hide failed verification.
- Include secrets, tokens, credentials, private account data, or raw environment dumps in training examples.
- Turn dataset generation into product runtime behavior.

## Cloud Model Roles

Cloud models should remain part of the training loop:

- Teacher: generate ideal traces for narrow Karkhana tasks using repo context and the episode schema.
- Critic: review candidate episodes for hallucinated files, unsafe actions, missing verification, and weak final reports.
- Rescue worker: produce corrected traces after a local worker fails, preserving the failed attempt as useful training signal.
- Dataset generator: create candidate JSONL episodes from prompts, raw logs, and benchmark tasks.

Cloud output is not accepted automatically. It becomes candidate data that must pass schema validation, privacy scrubbing, deduplication, and quality labeling.

## Worker Trace Types

Successful worker traces show the full inspect-plan-edit-verify-report loop for a bounded task.

Failed worker traces are useful when they show honest failure: the worker inspected relevant context, avoided unsafe changes, captured the error, and reported what should happen next.

Cloud-rescued traces pair a failed local attempt with a stronger teacher or rescue trajectory. These examples teach the local model when to escalate and how a recovery should look.

Reviewer and critic traces teach judgment. They should identify architecture violations, missing tests, overbroad edits, privacy leaks, and false claims without becoming implementation tasks.

Future accepted worker traces from Karkhana should be converted into episodes by removing secrets, compressing large patches into summaries, preserving verification truth, labeling quality, and linking behavior to the relevant work item, project twin, local worker job, or build handoff concept.

