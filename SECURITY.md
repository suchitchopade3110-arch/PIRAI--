# Security Design

## Threat Model

The agent treats user messages, conversation history, retrieved documents, model output, and tool requests as separate security sources. An attacker may try to override application policy, extract protected context, poison retrieved data, claim permissions, trigger unauthorized tools, or cause sensitive output.

The enforced instruction hierarchy is:

```text
System / application policy
  > Trusted application state and permissions
  > User request
  > External or retrieved content
```

Authorization comes only from trusted application state. Natural-language claims such as “I am the admin” never grant permission.

## Attack Categories

The centralized `AttackCategory` taxonomy covers direct and indirect prompt injection, system-prompt extraction, role hijacking, safety bypass, obfuscated and multi-turn jailbreaks, context poisoning, tool abuse, privilege escalation, data exfiltration, and unknown adversarial input.

## Security Pipeline

```text
Input -> bounded normalization -> attack/history detection
      -> retrieved-context analysis -> content moderation -> policy
      -> tool permission gate -> model execution
      -> output moderation -> secret/internal-content scan -> response
```

Blocked or review-bound inputs never invoke the model. Rejected tool requests never execute. Malicious retrieved instructions are ignored while the legitimate user task may continue without the poisoned context.

## Detection Strategy

Deterministic controls use bounded Unicode normalization, zero-width removal, conservative leetspeak handling, character-spacing recovery, and limited inspection of reversed or Base64-like text. Inspection is capped by character and history limits to reduce denial-of-service risk. Educational discussion is allowed unless the text contains an instruction aimed at changing the agent’s behavior or permissions.

## Policy Decisions

- `ALLOW`: continue through the next control.
- `REVIEW`: stop before execution and require human review.
- `BLOCK`: stop the request or output.
- `REDACT`: replace sensitive output without exposing the matched value.
- `IGNORE`: discard a malicious instruction found in untrusted context and continue the safe task.

Existing moderation thresholds remain defined in `config.py`.

## Tool Security

Every tool request is checked against a centralized allowlist containing permitted actions, required trusted permission, risk level, and basic argument validation. Tool execution requires an application-supplied permission set and an explicit executor callback. Prompt text cannot populate trusted permissions.

## Output Security

Generated output passes through the existing moderation classifier and a deterministic scan for likely credentials, protected prompt material, and tool-policy bypass instructions. Audit events record metadata only; raw prompts, secrets, passwords, and protected instructions are not logged.

## Evaluation

Run the deterministic local suite without downloading models:

```bash
python -m unittest discover -s tests -v
python demo.py
```

The dashboard summary executes the local fixture set and derives totals, decisions, false positives, false negatives, bypass rate, and safe-request pass rate from those results. It does not hard-code passing outcomes.

## Demo Instructions

Run `python web_server.py`, open `http://127.0.0.1:8080`, select an attack case, and choose **Run test**. The interface compares the insecure baseline with protected execution, displays the backend trace, and lists execution-derived results for every category.

## Limitations

Pattern and classifier-based defenses reduce common prompt-injection attacks but cannot guarantee complete prevention against future adversarial prompts. The deterministic decoder intentionally supports only bounded, common transformations. Semantic attacks may require a dedicated classifier. Tool policies cover registered tools only and must be expanded when real tools are added. Secret scanning is heuristic and should complement—not replace—secret managers, output schemas, least privilege, and sandboxing.
