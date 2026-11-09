#!/usr/bin/env python3
"""PADRE MX V3: deterministic two-audit/two-repair authorization and provenance.
This software cannot judge literary logic; a full independent editorial read is required.
Commands: audit, contract, repair, final. This file is bundled in auditor and writer SKILLs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

AUDIT_SCHEMA = "PADRE_MX_AUDIT_FROZEN_V3"
CONTRACT_SCHEMA = "PADRE_MX_REPAIR_CONTRACT_V3"
PROOF_SCHEMA = "PADRE_MX_REPAIR_PROOF_V3"
FINAL_SCHEMA = "PADRE_MX_QA_FINAL_V3"
LOGIC_TYPES = {
    "LOGIC",
    "CAUSALITY",
    "DIALOGUE",
    "TIMELINE",
    "SPACE",
    "MONEY",
    "MOTIVATION",
    "KNOWLEDGE",
    "ACCESS",
    "LEGAL",
    "PHYSICAL",
    "NAME",
    "CONTINUITY",
    "EVIDENCE",
    "SETUP_PAYOFF",
}
QUALITY_TYPES = LOGIC_TYPES | {
    "HOOK",
    "RETENTION",
    "PACING",
    "EMOTION",
    "CHARACTER",
    "STRUCTURE",
    "TWIST",
    "ENDING",
    "ORTHOGRAPHY",
    "GRAMMAR",
    "PUNCTUATION",
    "ES_MX",
    "TTS",
    "STYLE",
    "LENGTH",
    "REALISM",
    "REPETITION",
}
HEADINGS = re.compile(rb"(?m)^\[PART ([1-7])\]\n")


def fail(x):
    raise ValueError(str(x))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canonical(d):
    return json.dumps(
        d, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def get_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_locked(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        fail("Output exists; frozen artifacts cannot be overwritten: " + str(path))
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def check_seal(item, key):
    if not isinstance(item, dict):
        fail("Frozen object must be JSON object")
    if sha(canonical({k: v for k, v in item.items() if k != key})) != item.get(key):
        fail("Frozen artifact seal mismatch: " + key)


def sign(item, key):
    item[key] = sha(canonical(item))
    return item


def identity(title, outline_path):
    b = Path(outline_path).read_bytes()
    b.decode("utf-8", "strict")
    if "\r" in b.decode():
        fail("Outline must use LF only")
    osh = sha(b)
    return {
        "locked_title": title,
        "outline_sha256": osh,
        "video_id": sha((title + "\n" + osh).encode("utf-8"))[:16],
    }


def content_check(script):
    b = Path(script).read_bytes()
    t = b.decode("utf-8", "strict")
    if b.startswith(b"\xef\xbb\xbf") or "\r" in t:
        fail("Script must be UTF-8 without BOM and LF-only")
    heads = list(HEADINGS.finditer(b))
    if [int(h.group(1)) for h in heads] != list(range(1, 8)):
        fail("Exactly ordered [PART 1]..[PART 7] heading lines are required")
    # Each Part byte block is converted to unicode codepoints.
    parts = []
    for i, h in enumerate(heads):
        start = h.end()
        end = heads[i + 1].start() if i + 1 < 7 else len(b)
        parts.append(b[start:end].decode("utf8", "strict"))
    lengths = [len(p) for p in parts]
    total = sum(lengths)
    if not (70000 <= total <= 80000) or min(lengths) < 8500:
        fail(
            "Length gate FAIL (body 70-80k and each Part >=8500): total="
            + str(total)
            + " parts="
            + str(lengths)
        )
    # V3 accepts stage-ranges in authored segment manifest, but audit can't infer exact A/B/C byte manifest.
    return {
        "raw": b,
        "parts": parts,
        "lengths": lengths,
        "total": total,
        "sha": sha(b),
        "heading_matches": heads,
    }


def checked_audit(a, b, ident=None, expected_round=None):
    if a.get("schema") != AUDIT_SCHEMA:
        fail("Expected V3 audit artifact")
    check_seal(a, "manifest_sha256")
    if a.get("source_sha256") != sha(b):
        fail("Frozen audit does not match exact script bytes")
    if ident and any(a.get(k) != v for k, v in ident.items()):
        fail("Script/outline/title identity mismatch in audit")
    if expected_round and a.get("audit_round") != expected_round:
        fail("Incorrect frozen audit round")


def evidence_span(raw, part, text):
    if not isinstance(text, str) or len(text) < 18:
        fail("Part evidence must be >=18 characters and source-exact")
    m = list(HEADINGS.finditer(raw))
    i = part - 1
    target = raw[m[i].end() : m[i + 1].start() if i < 6 else len(raw)]
    if text.encode("utf-8") not in target:
        fail("Evidence quote not present in indicated Part " + str(part))


def validate_issue(issue, allowed, raw):
    fields = [
        "id",
        "severity",
        "category",
        "part",
        "anchor",
        "problem",
        "acceptance_tests",
    ]
    for f in fields:
        if f not in issue:
            fail("Missing issue field " + f)
    if issue["category"] not in allowed:
        fail("Issue type not allowed in this audit: " + str(issue["category"]))
    if issue["severity"] not in ("P0", "P1", "P2", "P3"):
        fail("Issue severity invalid")
    if type(issue["part"]) != int or not 1 <= issue["part"] <= 7:
        fail("Issue Part invalid")
    evidence_span(raw, issue["part"], issue["anchor"])
    if not isinstance(issue["problem"], str) or len(issue["problem"].strip()) < 12:
        fail("Issue problem must explain specific fault")
    if not isinstance(issue["acceptance_tests"], list) or not issue["acceptance_tests"]:
        fail("Acceptance tests missing")
    if issue.get("status", "CONFIRMED") not in ("CONFIRMED", "SUSPECTED"):
        fail("Issue status must be CONFIRMED or SUSPECTED")


def audit(ns):
    if ns.round not in (1, 2):
        fail("Only two audit rounds")
    snap = content_check(ns.script)
    raw = snap["raw"]
    ident = identity(ns.title, ns.outline_file)
    r = get_json(ns.review)
    if r.get("audit_round") != ns.round:
        fail("Review round differs from invocation")
    focus = "LOGIC" if ns.round == 1 else "COMPREHENSIVE"
    if r.get("focus") != focus:
        fail("Expected review focus " + focus)
    cov = r.get("coverage", {})
    if (
        not isinstance(cov, dict)
        or cov.get("total_ranges", 0) < 1
        or cov.get("reviewed_ranges") != cov["total_ranges"]
        or cov.get("unread_ranges") != []
    ):
        fail(
            "All text ranges must be independently reviewed; cannot freeze incomplete coverage"
        )
    if cov.get("reviewed_parts") != list(range(1, 8)):
        fail("Every Part must be fully checked")
    ev = r.get("evidence_per_part")
    if not isinstance(ev, dict):
        fail("Provide exact quote evidence for every Part")
    for i in range(1, 8):
        evidence_span(raw, i, ev.get(str(i)))
    score = r.get("score")
    if type(score) not in (int, float) or not 0 <= score <= 100:
        fail("Score 0..100 required")
    issues = r.get("issues")
    if not isinstance(issues, list):
        fail("Full issue ledger required (possibly empty)")
    ids = set()
    for issue in issues:
        if not isinstance(issue, dict):
            fail("Issue entries must be objects")
        validate_issue(issue, LOGIC_TYPES if ns.round == 1 else QUALITY_TYPES, raw)
        if issue["id"] in ids:
            fail("Duplicate issue ID")
        ids.add(issue["id"])
    spans = r.get("pass_spans", [])
    if not isinstance(spans, list):
        fail("pass_spans must be a list")
    sid = set()
    for s in spans:
        if (
            not isinstance(s, dict)
            or not s.get("id")
            or not s.get("text")
            or s["text"].encode("utf8") not in raw
        ):
            fail("PASS span must be an exact quote from script")
        if s["id"] in sid:
            fail("Duplicate PASS span id")
        sid.add(s["id"])
    previous = None
    if ns.round == 2:
        if not ns.previous_audit:
            fail("Round 2 must reference frozen round 1")
        p = get_json(ns.previous_audit)
        if p.get("schema") != AUDIT_SCHEMA or p.get("audit_round") != 1:
            fail("Previous audit must be round 1")
        check_seal(p, "manifest_sha256")
        if any(p.get(k) != v for k, v in ident.items()):
            fail("Round 1 source identity mismatch")
        if ns.previous_proof:
            pr = get_json(ns.previous_proof)
            check_seal(pr, "proof_sha256")
            if pr.get("schema") != PROOF_SCHEMA or pr.get("repair_round") != 1:
                fail("Previous proof is not REPAIR 1")
            if (
                pr.get("source_sha256") != p["source_sha256"]
                or pr.get("revised_sha256") != snap["sha"]
                or pr.get("audit_sha256") != sha(Path(ns.previous_audit).read_bytes())
            ):
                fail("Round 1 repair provenance mismatch")
        else:
            if any(x.get("status", "CONFIRMED") == "CONFIRMED" for x in p["issues"]):
                fail("Round 1 had confirmed issues but no repair proof")
            if p["source_sha256"] != snap["sha"]:
                fail("Unchanged round1 source required when REPAIR 1 skipped")
        previous = {
            "round1_audit_sha256": sha(Path(ns.previous_audit).read_bytes()),
            "repair1_proof_sha256": sha(Path(ns.previous_proof).read_bytes())
            if ns.previous_proof
            else None,
        }
    confirmed = [i for i in issues if i.get("status", "CONFIRMED") == "CONFIRMED"]
    suspected = [i for i in issues if i.get("status") == "SUSPECTED"]
    state = (
        ("REPAIR_1_REQUIRED" if ns.round == 1 else "REPAIR_2_REQUIRED")
        if confirmed
        else ("BLOCKED_SUSPECTED" if suspected else "CLEAN")
    )
    data = {
        "schema": AUDIT_SCHEMA,
        "audit_round": ns.round,
        "focus": focus,
        **ident,
        "source_sha256": snap["sha"],
        "source_length": snap["total"],
        "part_lengths": snap["lengths"],
        "source_path": str(Path(ns.script).resolve()),
        "score": score,
        "coverage": cov,
        "evidence_per_part": ev,
        "issues": issues,
        "pass_spans": spans,
        "chronology": r.get("chronology", {}),
        "status": state,
        "previous_lineage": previous,
        "quality_limit": "Software verifies exact source quotes and lineage, not semantic completeness.",
    }
    sign(data, "manifest_sha256")
    dump_locked(ns.out, data)
    return {
        "pass": True,
        "audit_round": ns.round,
        "status": state,
        "issues": len(issues),
        "source_sha256": snap["sha"],
        "frozen": str(ns.out),
    }


def contract(ns):
    a = get_json(ns.audit)
    check_seal(a, "manifest_sha256")
    snap = content_check(ns.script)
    checked_audit(a, snap["raw"], expected_round=ns.round)
    if ns.round not in (1, 2):
        fail("Only repair round 1/2")
    confirmed = {
        i["id"]: i for i in a["issues"] if i.get("status", "CONFIRMED") == "CONFIRMED"
    }
    if not confirmed:
        fail("No confirmed issues; skip repair, do not create empty or extra repair")
    if any(i.get("status") == "SUSPECTED" for i in a["issues"]):
        fail(
            "Unresolved SUSPECTED issues must be investigated before locking repair contract"
        )
    zsrc = get_json(ns.zones).get("zones")
    if not isinstance(zsrc, list) or not zsrc:
        fail("Non-empty zones list required")
    headings = snap["heading_matches"]
    used = set()
    selected = set()
    zones = []
    prior = 0
    for z in sorted(zsrc, key=lambda z: z.get("start_byte", 0)):
        st, en = z.get("start_byte"), z.get("end_byte")
        zid = z.get("zone_id")
        names = z.get("issue_ids")
        if (
            type(st) != int
            or type(en) != int
            or st < prior
            or st >= en
            or en > len(snap["raw"])
        ):
            fail("Invalid overlapping UTF-8 byte ranges")
        if not zid or zid in used:
            fail("Duplicate or missing zone_id")
        used.add(zid)
        if (
            not isinstance(names, list)
            or not names
            or any(n not in confirmed for n in names)
        ):
            fail("Zone must refer only to confirmed actual issue IDs")
        for h in headings:
            if st < h.end() and en > h.start():
                fail("Cannot edit heading line")
        snap["raw"][st:en].decode("utf8", "strict")
        for n in names:
            anchor = confirmed[n]["anchor"].encode("utf8")
            if anchor not in snap["raw"][st:en]:
                fail("Zone must contain exact anchor of issue " + n)
            selected.add(n)
        for s in a["pass_spans"]:
            q = s["text"].encode("utf8")
            loc = snap["raw"].find(q)
            while loc != -1:
                if st < loc + len(q) and en > loc:
                    allowed = z.get("pass_dependency_override_ids", [])
                    if (
                        ns.round != 2
                        or s["id"] not in allowed
                        or not z.get("pass_dependency_reason")
                        or len(z["pass_dependency_reason"]) < 35
                    ):
                        fail("Protected PASS span overlaps edit zone: " + s["id"])
                loc = snap["raw"].find(q, loc + 1)
        zones.append(
            {
                "zone_id": zid,
                "start_byte": st,
                "end_byte": en,
                "original_sha256": sha(snap["raw"][st:en]),
                "issue_ids": names,
                "pass_dependency_override_ids": z.get(
                    "pass_dependency_override_ids", []
                ),
                "pass_dependency_reason": z.get("pass_dependency_reason", ""),
            }
        )
        prior = en
    if selected != set(confirmed):
        fail(
            "Every confirmed issue must be assigned a zone: missing "
            + str(sorted(set(confirmed) - selected))
        )
    d = {
        "schema": CONTRACT_SCHEMA,
        "repair_round": ns.round,
        "video_id": a["video_id"],
        "locked_title": a["locked_title"],
        "outline_sha256": a["outline_sha256"],
        "source_sha256": snap["sha"],
        "audit_sha256": sha(Path(ns.audit).read_bytes()),
        "zones": zones,
        "authorized_issue_ids": sorted(selected),
    }
    sign(d, "contract_sha256")
    dump_locked(ns.out, d)
    return {
        "pass": True,
        "contract": str(ns.out),
        "repair_round": ns.round,
        "zones": len(zones),
        "issue_count": len(selected),
    }


def repair(ns):
    if ns.round not in (1, 2):
        fail("Maximum 2 repairs")
    if not ns.user_approved:
        fail("Require explicit user authorization for this repair invocation")
    sn = content_check(ns.script)
    raw = sn["raw"]
    idn = identity(ns.title, ns.outline_file)
    a = get_json(ns.audit)
    checked_audit(a, raw, idn, ns.round)
    c = get_json(ns.contract)
    check_seal(c, "contract_sha256")
    if c.get("schema") != CONTRACT_SCHEMA or c.get("repair_round") != ns.round:
        fail("Wrong repair contract schema/round")
    if (
        c["audit_sha256"] != sha(Path(ns.audit).read_bytes())
        or c["source_sha256"] != sn["sha"]
        or c["video_id"] != idn["video_id"]
    ):
        fail("Contract/source/audit does not match")
    inp = get_json(ns.replacements).get("replacements")
    zones = c.get("zones")
    if not isinstance(inp, list) or not isinstance(zones, list):
        fail("Malformed replacement JSON or contract")
    by = {x.get("zone_id"): x for x in inp}
    if len(by) != len(inp) or set(by) != {z["zone_id"] for z in zones}:
        fail("One and only one replacement for every authorized zone")
    if Path(ns.out).exists() or Path(ns.proof).exists():
        fail("Output/proof already exists, cannot replay")
    if Path(ns.out).resolve() == Path(ns.script).resolve():
        fail("Never overwrite source")
    output = bytearray()
    pr = 0
    changed = []
    new_segments = []
    for z in zones:
        st, en = z["start_byte"], z["end_byte"]
        if st < pr or sha(raw[st:en]) != z["original_sha256"]:
            fail("Source zone changed / overlaps")
        text = by[z["zone_id"]].get("text")
        if not isinstance(text, str) or not text.strip() or "\r" in text:
            fail("Replacement cannot be empty or CRLF")
        new = text.encode("utf8")
        if HEADINGS.search(new):
            fail("Do not rewrite [PART] headings")
        output += raw[pr:st]
        output += new
        new_segments.append((st, en, len(new)))
        changed.append(
            {
                "zone_id": z["zone_id"],
                "issue_ids": z["issue_ids"],
                "old_sha256": z["original_sha256"],
                "new_sha256": sha(new),
                "new_bytes": len(new),
            }
        )
        pr = en
    output += raw[pr:]
    data = bytes(output)
    if data == raw:
        fail("Repair claimed but script unchanged")
    # Invariant: every original unapproved segment is byte identical in new text.
    pos_old = pos_new = 0
    for st, en, n in new_segments:
        unchanged = raw[pos_old:st]
        if data[pos_new : pos_new + len(unchanged)] != unchanged:
            fail("Unauthorized byte change")
        pos_new += len(unchanged) + n
        pos_old = en
    if data[pos_new:] != raw[pos_old:]:
        fail("Unauthorized trailing byte change")
    tmp = Path(ns.out).with_suffix(".validation-temp.txt")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    if tmp.exists():
        fail("Temporary validation name already exists")
    try:
        tmp.write_bytes(data)
        test = content_check(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    lock = Path(ns.script).parent / (
        "PMX_" + idn["video_id"] + "_REPAIR_" + str(ns.round) + "_LOCK.json"
    )
    if lock.exists():
        fail(
            "This repair round has already been consumed for this video in this workspace"
        )
    Path(ns.out).write_bytes(data)
    if sha(Path(ns.out).read_bytes()) != sha(data):
        fail("Postwrite SHA verification failed")
    proof = {
        "schema": PROOF_SCHEMA,
        "repair_round": ns.round,
        **idn,
        "source_sha256": sn["sha"],
        "revised_sha256": sha(data),
        "audit_sha256": sha(Path(ns.audit).read_bytes()),
        "contract_sha256": sha(Path(ns.contract).read_bytes()),
        "revised_body_chars": test["total"],
        "revised_part_chars": test["lengths"],
        "untouched_bytes_verified": True,
        "changes": changed,
        "source_path": str(Path(ns.script).resolve()),
        "revised_path": str(Path(ns.out).resolve()),
        "editorial_validation": "Needs independent auditor verification, not self-certified READY",
    }
    sign(proof, "proof_sha256")
    dump_locked(ns.proof, proof)
    dump_locked(
        lock,
        {
            "video_id": idn["video_id"],
            "repair_round": ns.round,
            "proof_sha256": sha(Path(ns.proof).read_bytes()),
            "revised_sha256": sha(data),
        },
    )
    return {
        "pass": True,
        "round": ns.round,
        "revised_path": str(ns.out),
        "proof": str(ns.proof),
        "revised_sha256": sha(data),
        "next": "ROUND_2_AUDIT" if ns.round == 1 else "FINAL_VERIFY",
    }


def finalize(ns):
    snap = content_check(ns.script)
    idn = identity(ns.title, ns.outline_file)
    a1 = get_json(ns.round1_audit)
    a2 = get_json(ns.round2_audit)
    for ar, no in [(a1, 1), (a2, 2)]:
        check_seal(ar, "manifest_sha256")
        if ar.get("schema") != AUDIT_SCHEMA or ar.get("audit_round") != no:
            fail("Audit source is not V3 round " + str(no))
        if any(ar.get(k) != v for k, v in idn.items()):
            fail("Title/outline/video ID mismatches audit history")
    if a2.get("previous_lineage", {}).get("round1_audit_sha256") != sha(
        Path(ns.round1_audit).read_bytes()
    ):
        fail("Round 2 does not follow round 1")
    if ns.round1_proof:
        p1 = get_json(ns.round1_proof)
        check_seal(p1, "proof_sha256")
        if (
            p1["schema"] != PROOF_SCHEMA
            or p1["repair_round"] != 1
            or p1["source_sha256"] != a1["source_sha256"]
            or p1["revised_sha256"] != a2["source_sha256"]
        ):
            fail("First repair chain invalid")
        if a2["previous_lineage"].get("repair1_proof_sha256") != sha(
            Path(ns.round1_proof).read_bytes()
        ):
            fail("Round2 proof1 hash mismatch")
    elif a1["source_sha256"] != a2["source_sha256"] or any(
        i.get("status", "CONFIRMED") == "CONFIRMED" for i in a1["issues"]
    ):
        fail("Missing REPAIR1 proof")
    if ns.round2_proof:
        p2 = get_json(ns.round2_proof)
        check_seal(p2, "proof_sha256")
        if (
            p2["schema"] != PROOF_SCHEMA
            or p2["repair_round"] != 2
            or p2["source_sha256"] != a2["source_sha256"]
            or p2["revised_sha256"] != snap["sha"]
        ):
            fail("Second repair chain invalid")
        if p2["audit_sha256"] != sha(Path(ns.round2_audit).read_bytes()):
            fail("REPAIR2 not bound to frozen second audit")
    else:
        if any(i.get("status", "CONFIRMED") == "CONFIRMED" for i in a2["issues"]):
            fail("ROUND2 findings require REPAIR2 proof")
        if a2["source_sha256"] != snap["sha"]:
            fail("Without REPAIR2 source must equal audited R2 source")
    rev = get_json(ns.review)
    if rev.get("final_verification") is not True:
        fail("Final report must explicitly verify actual script")
    score = rev.get("score")
    if type(score) not in (int, float) or not 0 <= score <= 100:
        fail("Final score 0..100 required")
    remaining = rev.get("remaining_issues")
    new = rev.get("new_issues")
    if not isinstance(remaining, list) or not isinstance(new, list):
        fail("Full unresolved/new-issue lists are mandatory")
    if rev.get("integrity_checked") is not True:
        fail("Final integrity not actually checked")
    resolved = rev.get("resolved_issue_ids")
    if not isinstance(resolved, list):
        fail("resolved_issue_ids list missing")
    required = {
        i["id"] for i in a2["issues"] if i.get("status", "CONFIRMED") == "CONFIRMED"
    }
    if not required.issubset(set(resolved)):
        fail("Some confirmed round 2 issues are not reported resolved")
    # Preserve PASS text after repair2. Editorial override must cite source and a specific dependent issue.
    changes = []
    for span in a2.get("pass_spans", []):
        if span["text"].encode("utf8") not in snap["raw"]:
            changes.append(span["id"])
    overrides = rev.get("pass_span_dependency_overrides", {})
    if not isinstance(overrides, dict):
        fail("pass_span_dependency_overrides must be object")
    illegal = [x for x in changes if len(str(overrides.get(x, ""))) < 35]
    if illegal:
        fail(
            "Protected PASS spans modified without causal justification: "
            + str(illegal)
        )
    ready = (
        score >= 95
        and not remaining
        and not new
        and not any(i.get("status") == "SUSPECTED" for i in a2["issues"])
    )
    status = "PASS_PUBLISH_READY" if ready else "NOT_PUBLISH_READY"
    final = {
        "schema": FINAL_SCHEMA,
        **idn,
        "status": status,
        "score": score,
        "script_sha256": snap["sha"],
        "script_body_chars": snap["total"],
        "part_chars": snap["lengths"],
        "round1_audit_sha256": sha(Path(ns.round1_audit).read_bytes()),
        "round2_audit_sha256": sha(Path(ns.round2_audit).read_bytes()),
        "round1_proof_sha256": sha(Path(ns.round1_proof).read_bytes())
        if ns.round1_proof
        else None,
        "round2_proof_sha256": sha(Path(ns.round2_proof).read_bytes())
        if ns.round2_proof
        else None,
        "remaining_issues": remaining,
        "new_issues": new,
        "resolved_issue_ids": resolved,
        "pass_spans_preserved": len(changes) - len(illegal),
        "pass_spans_changed_with_evidence": changes,
        "editorial_note": "Mechanically verified provenance and structural constraints; semantic judgement comes from editor-entered final review.",
    }
    sign(final, "manifest_sha256")
    dump_locked(ns.out, final)
    return {
        "pass": True,
        "status": status,
        "final_score": score,
        "script_sha256": snap["sha"],
        "final_qa_path": str(ns.out),
        "unresolved_issues": len(remaining) + len(new),
    }


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for cmd in ("audit", "contract", "repair", "final"):
        p = sub.add_parser(cmd)
        p.add_argument("--script", type=Path, required=True)
        p.add_argument("--out", type=Path, required=True)
        if cmd != "contract":
            p.add_argument("--title", required=True)
            p.add_argument("--outline-file", type=Path, required=True)
        if cmd != "final":
            p.add_argument("--round", type=int, required=True)
        if cmd in ("audit", "final"):
            p.add_argument("--review", type=Path, required=True)
        if cmd == "audit":
            p.add_argument("--previous-audit", type=Path)
            p.add_argument("--previous-proof", type=Path)
        if cmd in ("contract", "repair"):
            p.add_argument("--audit", type=Path, required=True)
        if cmd == "contract":
            p.add_argument("--zones", type=Path, required=True)
        if cmd == "repair":
            p.add_argument("--contract", type=Path, required=True)
            p.add_argument("--replacements", type=Path, required=True)
            p.add_argument("--proof", type=Path, required=True)
            p.add_argument("--user-approved", action="store_true")
        if cmd == "final":
            p.add_argument("--round1-audit", type=Path, required=True)
            p.add_argument("--round2-audit", type=Path, required=True)
            p.add_argument("--round1-proof", type=Path)
            p.add_argument("--round2-proof", type=Path)
    args = parser.parse_args()
    try:
        result = globals()[args.command if args.command != "final" else "finalize"](
            args
        )
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        result = {"pass": False, "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    sys.exit(cli())
