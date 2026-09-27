# AI Security Demonstration

## Problem

Prompt injection and jailbreak attacks can make an AI coding agent ignore instructions, expose protected context, or bypass safety controls.

## Vulnerability

Without pre-generation controls, an adversarial request reaches the model boundary. The controlled baseline proves reachability but never asks the model to produce harmful content.

## Solution

```text
User Input
   ↓
Jailbreak Detector
   ↓
Input Moderation and Safety Policy
   ↓
Human Review when required
   ↓
Qwen Agent
   ↓
Output Moderation
   ↓
Safe Response
```

The live demo uses local deterministic moderation and generation fixtures so it runs without downloading model weights. The fixtures call the production policy function; the production application continues to use Qwen and the configured moderation model.

## Run

```bash
python demo.py
```

Optional modes: `python demo.py --baseline`, `python demo.py --protected`, and `python demo.py --case prompt_injection`.

## Evaluation

```bash
python main.py --evaluate
```

The existing benchmark command requires external benchmark access and locally available model dependencies.

## Demo Sequence

1. Identify the prompt-injection and jailbreak vulnerability.
2. Show attacks reaching the baseline generation boundary.
3. Run the same attacks through the protected pipeline.
4. Show a normal prompt reaching generation and being allowed.
5. Exercise the existing policy's deterministic human-review path.
6. Generate a before/after comparison from execution results.
7. Point to local audit logs and benchmark evidence.

The selector also includes indirect injection, context poisoning, role hijacking, safety bypass, obfuscation, multi-turn attacks, tool abuse, privilege escalation, data exfiltration, and safe educational requests. The summary table and rates are generated from local executions rather than hard-coded outcomes.
