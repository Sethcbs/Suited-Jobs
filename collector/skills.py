"""Keyword skill matcher (plan section 11), shared by jobs (1.0) and resumes (2.0)."""
import re
from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).parent.parent / "config" / "skills.yml"
# Whole-word edges that also work for names like C++, C#, .NET and Node.js
EDGE_BEFORE = r"(?<![\w+#.])"
EDGE_AFTER = r"(?![\w+#])"
# Stricter edges for exact-case short names like C and R ("R&D", "C-suite", "C.F.R.")
STRICT_BEFORE = r"(?<![\w+#.&/'-])"
STRICT_AFTER = r"(?![\w+#&/'.-])"


def load(path=DEFAULT_PATH):
    """Return a list of (standard_name, compiled_regex)."""
    cfg = yaml.safe_load(Path(path).read_text())
    patterns = []
    for name, aliases in (cfg.get("skills") or {}).items():
        alts = "|".join(re.escape(a) for a in aliases)
        patterns.append((str(name), re.compile(f"{EDGE_BEFORE}(?:{alts}){EDGE_AFTER}", re.I)))
    # "Schedule C", "Band, C": one lookbehind per word, since each must be fixed-width
    not_after = "".join(f"(?<!{re.escape(w)} )(?<!{re.escape(w)}, )"
                        for w in cfg.get("exact_case_not_after") or [])
    for name, aliases in (cfg.get("exact_case") or {}).items():
        alts = "|".join(re.escape(a) for a in aliases)
        patterns.append((str(name), re.compile(f"{STRICT_BEFORE}{not_after}(?:{alts}){STRICT_AFTER}")))
    return patterns


def find(text, patterns):
    """Standard names of every skill found in text, in config order."""
    return [name for name, rx in patterns if rx.search(text or "")]


def load_tech_rules(path=DEFAULT_PATH):
    """Return (general_skill_names, tech_title_regexes) for is_tech."""
    cfg = yaml.safe_load(Path(path).read_text())
    titles = "|".join(re.escape(t) for t in cfg.get("tech_titles") or [])
    exact = "|".join(re.escape(t) for t in cfg.get("tech_titles_exact_case") or [])
    regexes = [re.compile(f"{EDGE_BEFORE}(?:{titles}){EDGE_AFTER}", re.I),
               re.compile(f"{EDGE_BEFORE}(?:{exact}){EDGE_AFTER}")]
    return {str(s) for s in cfg.get("general") or []}, regexes


def is_tech(title, found, rules):
    """True if a job has a non-general skill or a tech title."""
    general, regexes = rules
    return bool(set(found) - general) or any(rx.search(title or "") for rx in regexes)
