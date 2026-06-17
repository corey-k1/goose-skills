"""Prompt sanitization helpers for FAL/Higgsfield generative calls.

Addresses LEARNINGS L6: FAL Seedance's `partner_validation_failed` content
filter fires on clinical/drug/death terminology. The fix is to keep prompts
metaphor-forward, not clinical. This module flags trigger words and suggests
softened alternatives.

Used by video-generation atoms (seedance/kling/veo3) and optionally image-gen
atoms. The check is advisory by default — emit a warning, don't block.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# Clinical / drug / death terms that commonly trigger content filters.
# Grouped so the warning can suggest a thematically appropriate replacement.
TRIGGER_GROUPS: dict[str, dict] = {
    "drugs": {
        "terms": [
            "cocaine", "heroin", "fentanyl", "methamphetamine", "meth ",
            "drug-laced", "laced with", "narcotic",
        ],
        "suggestion": "Use 'a substance', 'the test water', 'the labelled dropper', or a chemistry icon. Stay in metaphor.",
    },
    "death_explicit": {
        "terms": [
            "die", "died", "dying", "dead", "death", "kill", "killed",
            "corpse", "expire", "expired", "lifeless",
        ],
        "suggestion": "Use 'energy fades', 'they grow still', 'they rest peacefully', 'wisps drift up like quiet breath'. Imply, don't state.",
    },
    "violence_collapse": {
        "terms": [
            "collapse", "limp", "convulsing", "writhing", "wound",
            "bleeding", "violence", "violent",
        ],
        "suggestion": "Use 'they lower themselves down', 'they settle on the floor', 'they curl up motionless'. Softer language survives filters.",
    },
    "self_harm": {
        "terms": [
            "self-harm", "self harm", "suicide", "suicidal", "overdose",
            "cutting (skin)",
        ],
        "suggestion": "Reframe entirely — these terms reliably fail. Use abstract metaphors (e.g. 'a single figure under a heavy weight').",
    },
    "explicit_clinical": {
        "terms": [
            "hospital bed", "ICU", "emergency room", "ER scene",
            "syringe injection", "IV drip in arm",
        ],
        "suggestion": "Genericize: 'a clinical setting', 'a medical device', 'a lab dropper'. Don't anchor to specific medical equipment.",
    },
    "non_photoreal_routing": {
        # Not a filter trigger — a routing signal. If these appear, Seedance
        # is likely the wrong tool and ffmpeg-motion or Remotion is better.
        "terms": [
            "editorial illustration", "halftone", "2-tone", "spot illustration",
            "spot-illustration", "new yorker", "niemann", "steinberg",
            "flat 2d", "hand-drawn", "marker on paper", "pen on paper",
            "ascii", "isometric vector", "low-poly",
        ],
        "suggestion": "This aesthetic likely needs ffmpeg-motion (atoms/editing/ken-burns-clip) or Remotion, not generative i2v. See LEARNINGS L1.",
    },
}


@dataclass
class Finding:
    group: str
    matched: list[str]
    suggestion: str
    severity: str  # "warn" | "route"

    def __str__(self) -> str:
        return f"  [{self.severity.upper()}] {self.group}: matched {self.matched} → {self.suggestion}"


def scan(prompt: str) -> list[Finding]:
    """Return a list of findings — empty if the prompt looks clean."""
    findings: list[Finding] = []
    p = prompt.lower()
    for group, spec in TRIGGER_GROUPS.items():
        matched = []
        for term in spec["terms"]:
            # Word-boundary-ish match for terms (substring also works for phrases)
            pat = re.compile(r"\b" + re.escape(term) + r"\b") if " " not in term \
                else re.compile(re.escape(term))
            if pat.search(p):
                matched.append(term)
        if matched:
            severity = "route" if group == "non_photoreal_routing" else "warn"
            findings.append(Finding(
                group=group,
                matched=matched,
                suggestion=spec["suggestion"],
                severity=severity,
            ))
    return findings


def warn_to_stderr(prompt: str, *, tool_name: str = "") -> list[Finding]:
    """Convenience wrapper: scan + print findings to stderr. Returns findings."""
    import sys
    findings = scan(prompt)
    if findings:
        prefix = f"[prompt-sanitizer{':' + tool_name if tool_name else ''}]"
        print(f"{prefix} {len(findings)} concern(s) detected:", file=sys.stderr)
        for f in findings:
            print(f"{prefix} {f}", file=sys.stderr)
    return findings


if __name__ == "__main__":
    # CLI for testing: python3 prompt_sanitizer.py "your prompt here"
    import sys
    if len(sys.argv) < 2:
        sys.exit("usage: prompt_sanitizer.py <prompt>")
    findings = warn_to_stderr(" ".join(sys.argv[1:]))
    sys.exit(1 if findings else 0)
