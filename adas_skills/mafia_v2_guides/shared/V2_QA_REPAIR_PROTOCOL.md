# V2.0 FORENSIC QA + CONTROLLED REPAIR PROTOCOL

## Audit stages
**READ 1 — logic:** story and outline fidelity, time/place, knowledge, evidence custody, heroine agency, power dynamics, antagonist motive, physical constraints, causal bridges, loop closure, title payoff. Build a map of all Parts; do not repair yet.

**READ 2 — full quality:** American-English prose, pacing, redundant exposition, retention progress, consent/safety, TTS contamination, Part numbering, length, dialogue and smooth handoffs. Re-scan READ 1 defects after making the complete map. An audit with no findings is not proof of perfect story quality.

## Source locks
Store exact SHA-256 for title, outline, original script (OPB) and current script (CRB), and continuity ledger. Compare actual files before marking `READY`. Record one exact quote per Part to verify that the audit references the supplied current script. These anchors and the self-reported double read **cannot prove** the reviewer read every line; use them as minimum traceability, not as evidence of human-equivalent thoroughness.

## Severity & score
Use original 8-component rubric unchanged: A20/B20/C15/D10/E10/F10/G10/H5; P1=30%, P2=12%, P3=4% of one primary component, P0 zeroes its component and caps total at 59. Root issues scored once, with all repeated occurrences listed. `READY` means 0 actionable issues; preference never subtracts. User changing rules makes previous score non-comparable.

## Mode A — only review
Output complete issue ledger with IDs, P-level, component, PART, *exact quote* and occurrence positions, why it is actionable, proposed minimal repair, consequences and expected length impact. **Do not alter a single sentence**. Stop in `WAITING FOR REWRITE COMMAND` status; no auto-edit without explicit user authorization.

## Mode B — repair authorized changes
Require current CRB hash + patch IDs. For each patch, replace one unique, exact span in declared PART. Preserve every other byte of the source. No generating entire script again from memory. Repaired script automatically loses its previous READY certificate and continuity ledger; re-check both. OPB SHA never changes without explicit rebase. Keep total within 99–101% CRB if no net-length change approved; still aim for both standard word/char ranges. The tool refuses a third repair cycle unless a newly initialized/approved project lifecycle is used.

## Regression classification
`R` change-created defect, `L` latent defect missed earlier, `N` newly applicable, `P` preference only. An L defect is not evidence that the repair caused the issue. Re-audit can reveal new defects and reduce score, but report attribution accurately. Correct actual logic, not scores.

## Deliverable status
`NEEDS_PATCH`, `READY` or `BLOCKED`; never claim PASS with a stale SHA, missing script, unresolved P-level finding, or a target miss. When the verifier is unavailable, report `MECHANICAL VERIFICATION NOT RUN`.
