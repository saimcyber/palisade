# -*- coding: utf-8 -*-
"""Sanity-check M5-Resilience-Proof.docx: word count, stray markdown
markers (unclosed ** or `), and the no-time rule - same pattern as M4's
own verifier."""
import os
import re
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "M5-Resilience-Proof.docx")

TIME_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}"
    r"|\d{1,2} (?:January|February|March|April|May|June|July|August"
    r"|September|October|November|December)"
    r"|\bDay \d|\bDays \d"
    r"|\b\d+ (?:working )?days\b"
    r"|\b\d+ weeks?\b|\b\d+ months?\b"
    r"|half-day|working day"
    r"|\b\d+(?:\.\d+)? ?(?:min|mins|minutes|hours|hrs)\b"
    r"|\bdeadline\b|\bTimeline\b|\bDuration\b|\bCompleted on\b"
)
PROBES = ["2026-09-06", "Day 1", "Days 2-4", "20 working days",
          "half-day", "4.8 minutes", "deadline", "Timeline"]
broken = [p for p in PROBES if not TIME_PATTERN.search(p)]
if broken:
    raise SystemExit(f"SCANNER IS BROKEN - these should have matched: {broken}")

with zipfile.ZipFile(PATH) as z:
    xml = z.read("word/document.xml").decode("utf-8")

joined = re.sub(r"</w:t>\s*</w:r>\s*<w:r>(?:<w:rPr>.*?</w:rPr>)?\s*<w:t[^>]*>", "", xml)
text = re.sub(r"<[^>]+>", "", joined)
text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")

words = text.split()
print(f"word count: {len(words)}")

time_hits = sorted({m.group(0) for m in TIME_PATTERN.finditer(text)})
print(f"time-rule scan: {'CLEAN' if not time_hits else 'FAIL: ' + str(time_hits)}")

paragraphs = re.findall(r"<w:p[ >].*?</w:p>", joined, re.S)
stray = 0
for para in paragraphs:
    ptext = re.sub(r"<[^>]+>", "", para)
    if ptext.count("**") % 2 != 0:
        print("odd ** count in paragraph:", ptext[:120])
        stray += 1
    if ptext.count("`") % 2 != 0:
        print("odd ` count in paragraph:", ptext[:120])
        stray += 1
print(f"stray markdown markers: {stray}")

raise SystemExit(1 if (time_hits or stray) else 0)
