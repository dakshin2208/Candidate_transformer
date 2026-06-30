"""Skill normalization (doc 04: canonical dictionary lookup + alias removal).

Known aliases map to a canonical name (JS -> JavaScript). Exact canonical names
pass through. An UNKNOWN value is preserved as-is (trimmed), never dropped and
never guessed (doc 04: "Unknown skill alias -> Preserve original value, flag
for review"). The "flag for review" is recorded downstream at resolution time
(M5 provenance) — this function's contract is just: canonical-or-preserved.
"""
from __future__ import annotations

from typing import Optional

# lowercased alias -> canonical skill name.
_SKILL_ALIASES = {
    "js": "JavaScript", "javascript": "JavaScript",
    "ts": "TypeScript", "typescript": "TypeScript",
    "node": "Node.js", "nodejs": "Node.js", "node.js": "Node.js", "node js": "Node.js",
    "k8s": "Kubernetes", "kube": "Kubernetes", "kubernetes": "Kubernetes",
    "py": "Python", "python": "Python", "python3": "Python",
    "go": "Go", "golang": "Go",
    "rust": "Rust",
    "postgres": "PostgreSQL", "postgresql": "PostgreSQL", "psql": "PostgreSQL", "postgre": "PostgreSQL",
    "java": "Java",
    "csharp": "C#", "c#": "C#", "c sharp": "C#",
    "cpp": "C++", "c++": "C++",
    "react": "React", "reactjs": "React", "react.js": "React",
    "aws": "AWS", "amazon web services": "AWS",
    "gcp": "GCP", "google cloud": "GCP", "google cloud platform": "GCP",
    "tf": "Terraform", "terraform": "Terraform",
    "docker": "Docker",
    "ruby": "Ruby",
    "scala": "Scala",
    "kafka": "Kafka",
    "redis": "Redis",
    "mysql": "MySQL",
}


def normalize_skill(raw: Optional[str]) -> Optional[str]:
    """Canonicalize a skill name; preserve unknowns as-is.

    "JS" -> "JavaScript"   ·   "K8s" -> "Kubernetes"   ·   "Python" -> "Python"
    "SomeNicheTool" -> "SomeNicheTool"   (unknown: preserved, never dropped)
    "" / non-str -> None
    """
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None
    return _SKILL_ALIASES.get(s.lower(), s)
