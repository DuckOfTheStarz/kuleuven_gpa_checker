import re
import pdfplumber

# Title, 6-char course code (e.g. H02B1A), language, ECTS, grade, optional C/T/V flag
ROW_RE = re.compile(
    r"^(?P<title>.+?)\s+"
    r"(?P<code>[A-Z][0-9A-Z]{5})\s+"
    r"(?P<lang>[A-Z]{2})\s+"
    r"(?P<ects>\d+)\s+"
    r"(?P<grade>\d{1,2}|[A-Z/]{1,4})"      # numeric grade, or G/P, NG/F, V, ...
    r"(?:\s+(?P<flag>[CTV]))?$"
)
YEAR_RE = re.compile(r"Academiejaar\s+(\d{4}-\d{4})")

HONORS = [
    ("Cum fructu", 50),
    ("Cum laude", 68),
    ("Magna cum laude", 77),
    ("Summa cum laude", 85),
    ("Summa cum laude with congratulations", 90),
]
TOTAL_CREDITS = 120


def parse_transcript(pdf_path):
    courses = []
    year = None
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                line = line.strip()

                m = YEAR_RE.search(line)
                if m:
                    year = m.group(1)
                    continue

                m = ROW_RE.match(line)
                if m:
                    grade = m["grade"]
                    courses.append({
                        "year": year,
                        "code": m["code"],
                        "title": m["title"],
                        "lang": m["lang"],
                        "ects": int(m["ects"]),
                        "grade": int(grade) if grade.isdigit() else grade,
                        "flag": m["flag"],  # None if no credit marker (e.g. failed)
                    })
    return courses


def get_earned_credits(courses):
    return sum([c["ects"] for c in courses if (isinstance(c["grade"], int) and c["flag"])])

def get_credits_to_graduate(courses):
    return 120 - sum([c["ects"] for c in courses if (isinstance(c["grade"], int) and c["flag"])])

def get_ects(courses):
    total_credits = 0
    earned_credits = 0
    for c in courses:
        if (c["flag"]):
            total_credits += 20
            earned_credits += c["grade"]
    return(total_credits, earned_credits)

def get_avg(courses):
    graded = [c for c in courses if isinstance(c["grade"], int)]
    total_ects = sum(c["ects"] for c in graded)
    avg = sum(c["ects"] * c["grade"] for c in graded) / total_ects
    return(total_ects, avg)

def get_earned_avg(courses):
    graded = [c for c in courses if (isinstance(c["grade"], int) and c["flag"])]
    total_ects = sum(c["ects"] for c in graded)
    avg = sum(c["ects"] * c["grade"] for c in graded) / total_ects
    return(total_ects, avg)

def required_remaining_pct(courses, total_credits=TOTAL_CREDITS):
    earned, avg_20 = get_earned_avg(courses)   
    current_pct = avg_20 / 20 * 100
    remaining = total_credits - earned
    if remaining <= 0:
        return {"earned": earned, "remaining": 0, "current_pct": current_pct, "targets": {}}

    targets = {}
    for name, target in HONORS:
        needed = (target * total_credits - current_pct * earned) / remaining
        targets[name] = needed
    return {"earned": earned, "remaining": remaining, "current_pct": current_pct, "targets": targets}

def print_required_remaining(courses):
    r = required_remaining_pct(courses)
    print(f"\n{r['earned']} ECTS earned at {r['current_pct']:.2f}%, {r['remaining']} ECTS remaining.")
    print("Required average on the remaining credits:")
    for name, needed in r["targets"].items():
        if needed > 100:
            print(f"  It is not possible for you to graduate {name.lower()}."
                  f"(would need {needed:.2f}%)")
        elif needed <= get_credits_to_graduate(courses):
            print(f"  {name}: You are on track to graduate {name.lower()}."
                  f"(need {max(needed, get_credits_to_graduate(courses)):.2f}% or less)")
        else:
            print(f"  {name}: Requires an average of {needed:.2f}%  (= {needed / 5:.2f}/20) to graduate {name.lower()}.")

def print_earned_credits(courses):
    total_creds = get_earned_credits(courses)
    print(f"\n{total_creds} ECTS earned thus far.")

def print_avg(courses):
    (total_ects, avg) = get_avg(courses)
    print(f"\n{total_ects} ECTS, weighted avg: {avg:.2f}/20 = {avg / 20 * 100:.2f}%")

def print_earned_avg(courses):
    (total_ects, avg) = get_earned_avg(courses)
    print(f"\n{total_ects} ECTS, weighted avg: {avg:.2f}/20 = {avg / 20 * 100:.2f}%")

def print_course_roster(courses):
    for c in courses:
            print(f"{c['code']} | {c['ects']} ECTS | {c['grade']}/20 | {c['flag'] or '-'} | {c['title']}")

def print_ects(courses):
    (total_creds, earned_creds) = get_ects(courses)
    print(f"\n{earned_creds} points earned out of {total_creds}")




if __name__ == "__main__":
    courses = parse_transcript("Bijlage 01-2.PDF")
    print_course_roster(courses)
    print_avg(courses)
    print_earned_avg(courses)
    print_ects(courses)
    print_earned_credits(courses)
    print_required_remaining(courses)