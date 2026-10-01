# PIRAI Governance

## Governance goals

PIRAI makes automated and exceptional human security decisions attributable, policy-bound, explainable, reviewable, and auditable. Its governing principle is:

> AI proposes or classifies. Policy constrains. Humans remain accountable for exceptional decisions. Every important action leaves an auditable record.

## Responsibility boundaries

The safety classifier supplies scores; deterministic detectors identify explicit attacks; the active policy converts those signals into `ALLOW`, `REVIEW`, or `BLOCK`; trusted application code enforces tool permissions; authorized reviewers resolve exceptional cases. Prompt text, retrieved documents, model output, and claims such as “I am the administrator” cannot grant reviewer or tool authority.

Operators own storage availability and retention. Policy owners approve new policy versions. Reviewers own the decisions and justifications they submit. Application maintainers preserve the fail-closed enforcement boundary.

## Automated decision lifecycle

Each major decision receives an `EVT-*` identifier and records its stage, outcome, category, score, risk, invocation status, active policy, model identifiers, tool-policy version, and timestamp. `ALLOW` continues through the existing protected pipeline. `BLOCK` stops execution. `REVIEW` must be persisted before the response is returned and never automatically continues execution.

## Human review lifecycle

`REVIEW` creates an append-only `REV-*` record in `results/governance_reviews.jsonl` with `PENDING` status. A trusted application action may resolve it exactly once as `APPROVED` or `REJECTED`. Resolution adds reviewer identity, mandatory justification, and resolution time as a new journal entry. The original automated event and initial review entry remain unchanged.

Approval records a governance outcome; it does not silently replay the original request or bypass input, tool, output, or sensitive-data controls. Any later execution must enter through an explicitly designed trusted workflow and pass applicable controls again.

## Reviewer responsibilities

Reviewers must use their assigned identity, inspect the stated risk and policy version, document a concrete rationale, avoid copying sensitive prompt or output content into the justification, and reject cases whose safety cannot be established. Shared or anonymous reviewer identifiers are prohibited operationally.

## Approval and rejection

The local API accepts `APPROVED` or `REJECTED` plus nonblank `reviewer_id` and `justification`. Unknown IDs fail, and resolved records are immutable. Reviewer authority is trusted application input; this demo API is bound to localhost and is not an authentication system.

## Overrides

Overrides are exceptional, append-only `OVR-*` records in `results/governance_overrides.jsonl`. They require an existing automated audit event, a matching original `BLOCK` or `REVIEW` decision, reviewer identity, reason, final governed decision, timestamp, and policy version. When a review ID is supplied, it must match the event. Overrides never edit or delete the automated event or review history.

## Policy versioning and configuration provenance

`governance/policy_registry.py` exposes the active `PIRAI-POLICY-1.0.0` configuration from centralized settings. The snapshot includes review, block, and zero-tolerance thresholds; zero-tolerance categories; safety and coding model identifiers; tool-policy version; and activation metadata. Historical events embed their policy and model provenance so later configuration changes do not make them uninterpretable.

Policy changes require a new identifier, reviewed configuration changes, updated tests, and documentation. Reusing an identifier for changed semantics is prohibited.

## Audit retention

Security events, review journals, override journals, and generated reports live under `results/`. JSONL files are append-oriented and flushed to durable local storage. Production operators must define access control, backup, rotation, retention duration, and legal-hold procedures appropriate to their deployment; the repository does not automate deletion or cloud retention.

## Privacy-preserving audit principles

Governance stores identifiers and decision metadata, not raw prompts, raw blocked output, passwords, API keys, tokens, system prompts, developer instructions, detector signatures, or chain-of-thought. Reviewer justifications must describe policy evidence without reproducing sensitive content. Prompt IDs should be opaque application identifiers.

## Transparency boundaries

Public explanations expose the observable decision, event and review IDs, category, risk level, confidence or score where available, applicable threshold, policy version, safe reason, recommended action, and model/tool invocation status. They do not expose hidden reasoning or confidential instructions.

## Governance reporting

`governance/governance_report.py` derives counts from the actual security event, latest review state, and override journals. It reports decisions, review states, overrides, risk and policy groupings, tool denials, human-reviewed cases, resolution rate, resolution time, and active model/policy provenance. Missing review data is stated as insufficient rather than treated as success. `POST /api/governance/report` refreshes `results/governance_report.json`.

## Incident and audit investigation

Start with an `event_id`, identify its policy and participating models, correlate any `review_id` and `override_id`, verify invocation flags, and compare timestamps and justifications. Preserve the append-only source files before analysis. Investigators should distinguish the original automated decision from the final governed outcome and document any storage gaps or legacy unversioned events.

## Known limitations

- The local HTTP demo has strict validation but no production authentication or role system; deploy it only behind trusted access controls.
- JSONL storage provides lightweight local durability and process-level serialization, not distributed transactions or multi-host coordination.
- Review approval records accountability but intentionally does not auto-execute a paused request.
- Existing historical audit rows predate event and policy identifiers and are reported as `LEGACY_UNVERSIONED`.
- Classifier, deterministic detection, and secret scanning limitations described in `SECURITY.md` still apply.
