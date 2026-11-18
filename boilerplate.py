# boilerplate.py - removes text that is about the company or the hiring process, not the job:
# "About <company>", pay ranges, benefits, equal-opportunity statements, how to apply, legal text.
# Used ONLY for the search chunks (retrieval). Skill counts and the stats still use the full post.
# Two rules, because the two sources look different:
#   1. Kaggle posts have line breaks + headings -> drop the section under a boilerplate heading
#      ("About TEKsystems", "Benefits:", "Equal Opportunity Statement"...) until the next heading.
#   2. Arbeitnow posts are one long line -> drop single sentences that match a boilerplate pattern.
# Safety rule (precision over recall): a line or sentence that names a skill, or a job fact
# (security clearance, on-site / hybrid / remote), is NEVER dropped.
import re

from skill_matcher import extract_skills

# --- 1. headings that start a boilerplate section ---
BOILER_HEADING = re.compile(
    r"^(?:company (?:overview|description|profile|information)|who we are|our (?:company|story|mission|culture)"
    r"|a little bit about us|benefits?(?: (?:&|and) perks)?|perks(?: (?:&|and) benefits)?|our benefits"
    r"|what we offer|what we can offer(?: you)?|why (?:join us|work (?:with|for) us)"
    r"|compensation(?: (?:&|and) benefits)?|salary|pay(?: range| transparency)?"
    r"|equal (?:employment )?opportunity(?: statement| employer)?|eeo(?: statement)?|diversity(?:,? equity)?(?: (?:&|and) inclusion)?"
    r"|how to apply|application process|our (?:interview|hiring) process|privacy notice)\s*:?$",
    re.IGNORECASE,
)
# "About X" is boilerplate when X is the company, but NOT "About the role / job / team / you"
ABOUT = re.compile(r"^about\s+(.{1,40}?)\s*:?$", re.IGNORECASE)
ABOUT_THE_JOB = re.compile(r"^(?:the |this )?(?:role|job|position|team|you|opportunity|the role)\b", re.IGNORECASE)


def is_heading(line):
    # a short line on its own, not a sentence: "Benefits:", "About TEKsystems", "Responsibilities"
    return 0 < len(line) <= 60 and len(line.split()) <= 7 and not line.endswith((".", ","))


def boiler_heading(line):
    if BOILER_HEADING.match(line):
        return True
    m = ABOUT.match(line)
    return bool(m) and not ABOUT_THE_JOB.match(m.group(1))


# --- 2. sentences that are boilerplate wherever they are ---
BOILER_SENTENCE = [
    ("equal opportunity", r"equal (?:employment )?opportunit|without regard to|affirmative action"
                          r"|reasonable accommodation|e-verify|protected (?:veteran|class|characteristic)"),
    ("pay", r"(?:pay|salary|compensation|wage) (?:range|band|scale)|base (?:pay|salary)|annual(?:ized)? salar"
            r"|\$\s?\d{2,3}(?:,\d{3}|k)|(?:£|€)\s?\d{2,3}(?:,\d{3}|k)|per hour|/hr\b|\bdoe\b"
            r"|incentive compensation|performance bonus|stock options?|compensation packages?|base compensation"
            r"|salary ranges?|offer amounts?|cost of labou?r"),
    ("benefits", r"401\(?k\)?|(?:health|medical|dental|vision) (?:insurance|benefits|coverage|plans?)"
                 r"|paid time off|\bpto\b|parental leave|holiday allowance|competitive (?:salary|compensation|benefits)"),
    ("apply / legal", r"by submitting (?:an|your|this) application|how to apply|apply (?:now|today)"
                      r"|(?:want|love|like) to hear from you|please (?:contact|send|submit|apply)"
                      r"|for more information,? (?:please )?visit|careers? (?:website|page|site)"
                      r"|find jobs in .{1,40} on arbeitnow|employment authori[sz]ation|visa sponsorship|sponsorship"
                      r"|will (?:not )?(?:consider )?sponsor"
                      r"|privacy (?:policy|notice)|background check"),
]
BOILER_SENTENCE = [(name, re.compile(p, re.IGNORECASE)) for name, p in BOILER_SENTENCE]
# job facts that sit in HR-style sentences: a security clearance, on-site / hybrid / remote work.
# A line or sentence with one of these is kept, like a line with a skill.
JOB_FACT = re.compile(r"clearance|polygraph|\bTS/SCI\b|\bon-?site\b|\bhybrid\b|\bremote\b", re.IGNORECASE)


def must_keep(text):
    return bool(extract_skills(text)) or bool(JOB_FACT.search(text))


# sentence ends: ". " / "! " / "? " followed by a capital letter or a quote, or a line break
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")


def boiler_kind(sentence):
    for name, pattern in BOILER_SENTENCE:
        if pattern.search(sentence):
            return name
    return None


def strip_boilerplate(text, removed=None):
    """Returns the text without boilerplate. If `removed` is a list, every removed piece is
    appended to it as (kind, text), so a preview can show exactly what was cut."""
    keep_line = []
    skipping = False
    for line in text.split("\n"):
        s = line.strip()
        if is_heading(s):
            if boiler_heading(s):
                skipping = True
                if removed is not None:
                    removed.append(("section heading", s))
                continue
            skipping = False  # a normal heading ends the boilerplate section
        if skipping and s:
            if must_keep(s):  # safety rule: a line with a skill or a job fact stays
                keep_line.append(line)
            elif removed is not None:
                removed.append(("section", s))
            continue
        keep_line.append(line)

    out_lines = []
    for line in keep_line:
        kept = []
        for sentence in SENTENCE_END.split(line):
            kind = boiler_kind(sentence)
            if kind and not must_keep(sentence):
                if removed is not None:
                    removed.append((kind, sentence.strip()))
                continue
            kept.append(sentence)
        out_lines.append(" ".join(kept))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out_lines)).strip()
