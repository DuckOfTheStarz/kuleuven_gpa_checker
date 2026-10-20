import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pdfplumber



ROW_RE = re.compile(
    r"^(?P<title>.+?)\s+"
    r"(?P<code>[A-Z][0-9A-Z]{5})\s+"
    r"(?P<lang>[A-Z]{2})\s+"
    r"(?P<ects>\d+)\s+"
    r"(?P<grade>\d{1,2}|[A-Z/]{1,4})"
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
DEFAULT_TOTAL_CREDITS = 120
PASS_PCT = 50  # 10/20

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
                        "flag": m["flag"],  # None if no credit marker (failed)
                    })
    return courses


def analyze(courses, total_credits):
    graded = [c for c in courses if isinstance(c["grade"], int)]
    earned_courses = [c for c in graded if c["flag"]]

    earned = sum(c["ects"] for c in earned_courses)
    earned_pts = sum(c["ects"] * c["grade"] for c in earned_courses)
    earned_avg20 = earned_pts / earned if earned else 0.0
    current_pct = earned_avg20 / 20 * 100

    all_ects = sum(c["ects"] for c in graded)
    all_avg20 = sum(c["ects"] * c["grade"] for c in graded) / all_ects if all_ects else 0.0

    remaining = max(total_credits - earned, 0)

    honors = []
    for name, target in HONORS:
        if remaining == 0:
            verdict = "Achieved" if current_pct >= target else "Not achieved"
            needed = None
        else:
            needed = (target * total_credits - current_pct * earned) / remaining
            if needed > 100:
                verdict = "Not possible"
            elif needed <= PASS_PCT:
                verdict = "Secured if you pass everything"
            else:
                verdict = "Possible"
        honors.append({"name": name, "target": target, "needed": needed, "verdict": verdict})

    return {
        "earned": earned,
        "remaining": remaining,
        "total_credits": total_credits,
        "earned_avg20": earned_avg20,
        "current_pct": current_pct,
        "all_ects": all_ects,
        "all_avg20": all_avg20,
        "all_pct": all_avg20 / 20 * 100,
        "failed": [c for c in courses if isinstance(c["grade"], int) and not c["flag"]],
        "honors": honors,
    }


def show_results(parent, courses, a):
    win = tk.Toplevel(parent)
    win.title("Transcript results")
    win.geometry("860x700")
    win.minsize(700, 520)

    outer = ttk.Frame(win, padding=14)
    outer.pack(fill="both", expand=True)

    # --- summary ---
    summary = ttk.LabelFrame(outer, text="Summary", padding=10)
    summary.pack(fill="x")
    rows = [
        ("Credits earned", f"{a['earned']} / {a['total_credits']}  ({a['remaining']} remaining)"),
        ("Average of earned courses",
         f"{a['earned_avg20']:.2f}/20  =  {a['current_pct']:.2f}%"),
        ("Average of all graded courses",
         f"{a['all_avg20']:.2f}/20  =  {a['all_pct']:.2f}%  ({a['all_ects']} ECTS)"),
        ("Failed / not yet passed",
         f"{len(a['failed'])} course(s), {sum(c['ects'] for c in a['failed'])} ECTS"),
    ]
    for i, (k, v) in enumerate(rows):
        ttk.Label(summary, text=k + ":", font=("TkDefaultFont", 10, "bold")).grid(
            row=i, column=0, sticky="w", padx=(0, 12), pady=2)
        ttk.Label(summary, text=v).grid(row=i, column=1, sticky="w", pady=2)

    # --- courses ---
    cframe = ttk.LabelFrame(outer, text="Courses", padding=6)
    cframe.pack(fill="both", expand=True, pady=(10, 0))
    cols = ("code", "title", "ects", "grade", "flag")
    tree = ttk.Treeview(cframe, columns=cols, show="headings", height=10)
    for col, text, width, anchor in [
        ("code", "Code", 70, "w"), ("title", "Title", 340, "w"),
        ("ects", "ECTS", 60, "center"), ("grade", "Grade /20", 80, "center"),
        ("flag", "Status", 70, "center"),
    ]:
        tree.heading(col, text=text)
        tree.column(col, width=width, anchor=anchor)
    tree.tag_configure("failed", foreground="#c0392b")
    for c in courses:
        failed = isinstance(c["grade"], int) and not c["flag"]
        tree.insert("", "end", tags=("failed",) if failed else (),
                    values=(c["code"], c["title"], c["ects"], c["grade"], c["flag"] or "-"))
    sb = ttk.Scrollbar(cframe, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    hframe = ttk.LabelFrame(
        outer, text=f"Average needed on the remaining {a['remaining']} credits", padding=6)
    hframe.pack(fill="x", pady=(10, 0))
    hcols = ("honor", "target", "needed", "verdict")
    htree = ttk.Treeview(hframe, columns=hcols, show="headings", height=len(a["honors"]))
    for col, text, width, anchor in [
        ("honor", "Honours", 280, "w"), ("target", "Overall target", 100, "center"),
        ("needed", "Needed average", 150, "center"), ("verdict", "Verdict", 220, "w"),
    ]:
        htree.heading(col, text=text)
        htree.column(col, width=width, anchor=anchor)
    htree.tag_configure("no", foreground="#c0392b")
    htree.tag_configure("yes", foreground="#1e8449")
    for h in a["honors"]:
        if h["needed"] is None:
            needed_txt = "-"
        elif h["needed"] > 100:
            needed_txt = f"{h['needed']:.2f}%"
        else:
            shown = max(h["needed"], 0)
            needed_txt = f"{shown:.2f}%  ({shown / 5:.2f}/20)"
        tag = "no" if h["verdict"] in ("Not possible", "Not achieved") else "yes"
        htree.insert("", "end", tags=(tag,),
                     values=(h["name"], f"{h['target']}%", needed_txt, h["verdict"]))
    htree.pack(fill="x")

    ttk.Button(outer, text="Close", command=win.destroy).pack(anchor="e", pady=(10, 0))


def main():
    root = tk.Tk()
    root.title("KU Leuven Transcript Calculator")
    root.resizable(False, False)

    frm = ttk.Frame(root, padding=16)
    frm.pack()

    path_var = tk.StringVar()
    credits_var = tk.IntVar(value=DEFAULT_TOTAL_CREDITS)

    ttk.Label(frm, text="Transcript PDF:").grid(row=0, column=0, sticky="w", pady=4)
    ttk.Entry(frm, textvariable=path_var, width=45).grid(row=0, column=1, padx=6)

    def browse():
        p = filedialog.askopenfilename(
            title="Select transcript", filetypes=[("PDF files", "*.pdf *.PDF")])
        if p:
            path_var.set(p)

    ttk.Button(frm, text="Browse...", command=browse).grid(row=0, column=2)

    ttk.Label(frm, text="Total credits in programme:").grid(row=1, column=0, sticky="w", pady=4)
    ttk.Spinbox(frm, from_=1, to=300, textvariable=credits_var, width=6).grid(
        row=1, column=1, sticky="w", padx=6)

    def calculate():
        path = path_var.get().strip()
        if not path:
            messagebox.showwarning("No file", "Please select a transcript PDF first.")
            return
        try:
            total = int(credits_var.get())
        except (tk.TclError, ValueError):
            messagebox.showwarning("Invalid input", "Total credits must be a whole number.")
            return
        try:
            courses = parse_transcript(path)
        except Exception as e:
            messagebox.showerror("Could not read PDF", str(e))
            return
        if not courses:
            messagebox.showerror(
                "Nothing found",
                "No course rows were recognised in this PDF. "
                "Is it a KU Leuven transcript with selectable text?")
            return
        a = analyze(courses, total)
        show_results(root, courses, a)

    ttk.Button(frm, text="Calculate", command=calculate).grid(
        row=2, column=0, columnspan=3, pady=(14, 0))

    root.mainloop()


if __name__ == "__main__":
    main()
