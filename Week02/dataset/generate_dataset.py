"""
Generates a small, reasonably balanced synthetic dataset of document texts
for the Invoice / Resume / Other classes used by the project.

Why synthetic: Week 3 task asks us to "collect more suitable examples" and
"keep classes reasonably balanced". Real scanned invoices/resumes are not
available in this environment, so we simulate realistic OCR-style text
(varied formatting, some noise) for training + evaluating the classifier.
Students should REPLACE / EXTEND this with their own real collected samples
where possible (see README).
"""

import random
import csv

random.seed(42)

companies = ["ABC Technologies", "Bright Solutions Pvt Ltd", "Nova Traders",
             "Skyline Textiles", "Prime Logistics", "GreenLeaf Foods",
             "Falcon Electronics", "Metro Builders", "Zenith Consulting",
             "Orbit Software House"]

names = ["Ahmed Raza", "Sara Khan", "Bilal Hussain", "Ayesha Siddiqui",
         "Usman Tariq", "Hina Malik", "Fahad Iqbal", "Mahnoor Aslam",
         "Ali Hassan", "Zainab Farooq", "Hamza Sheikh", "Mariam Yousaf"]

skills_pool = ["Python", "SQL", "Machine Learning", "React", "Excel",
               "Data Analysis", "Java", "Project Management", "Streamlit",
               "Communication", "Photoshop", "AutoCAD", "Deep Learning",
               "Customer Service", "Accounting", "C++"]

other_topics = [
    "This agreement is made between the parties for the purpose of leasing "
    "office space located at Plot 12, Sector G-9, Islamabad for a period of "
    "two years starting from the date of signing.",
    "Meeting Minutes - Weekly Sync\nAttendees: project team\nAgenda: sprint "
    "review, blockers discussion, and planning for next sprint.\nAction "
    "items were assigned to respective owners.",
    "Terms and Conditions: Users must agree to the privacy policy before "
    "using this service. We collect only the data required to provide the "
    "service and do not share it with third parties.",
    "Weather report for today: partly cloudy with a chance of rain in the "
    "evening. Temperatures expected to range between 22C and 30C across "
    "the city.",
    "Research Paper Abstract: This study explores the impact of renewable "
    "energy adoption on rural electrification, using survey data collected "
    "from three provinces over a two year period.",
    "Grocery List\nMilk, Bread, Eggs, Rice, Cooking Oil, Vegetables, Fruits, "
    "Tea, Sugar, Detergent",
    "Certificate of Completion\nThis is to certify that the participant has "
    "successfully completed the online training program in Data Science "
    "fundamentals.",
    "Event Invitation: You are cordially invited to the annual tech "
    "conference to be held at the Convention Center. Please RSVP by the "
    "end of this week.",
    "Recipe: Chicken Biryani\nIngredients include rice, chicken, yogurt, "
    "onions and biryani masala. Cook on low heat for 20 minutes after "
    "layering.",
    "Newsletter: This month our team launched two new features and fixed "
    "several bugs reported by users. Read on for more updates and upcoming "
    "plans.",
    # Intentionally tricky "Other" examples that share vocabulary with
    # Invoice/Resume so the classifier is genuinely tested (not trivial).
    "Price Quotation\nDear customer, please find below our quotation for "
    "the requested items. Total estimated amount: $2,340. This quotation "
    "is valid for 15 days from the date of issue.",
    "Purchase Order\nOrder Number: PO-4521\nSupplier: Prime Logistics\n"
    "Please supply the following items by the due date. Payment will be "
    "made against invoice upon delivery.",
    "Course Syllabus - Data Analysis Fundamentals\nThis course covers key "
    "skills including spreadsheets, basic statistics, and data "
    "visualization. Prior education in mathematics is recommended.",
    "Job Posting: We are hiring a Project Coordinator. Required skills "
    "include communication, scheduling, and basic budgeting. Relevant "
    "experience in office administration is a plus.",
]


def ocr_noise(text: str, level: float = 0.15) -> str:
    """Randomly drop/garble a few characters to mimic imperfect OCR output."""
    if random.random() > level:
        return text
    chars = list(text)
    n_edits = max(1, int(len(chars) * 0.01))
    swaps = {"o": "0", "l": "1", "S": "5", "B": "8", "e": "e", "rn": "m"}
    for _ in range(n_edits):
        if not chars:
            break
        idx = random.randint(0, len(chars) - 1)
        c = chars[idx]
        if c.lower() in "ol sb":
            chars[idx] = random.choice(["0", "1", " "])
    return "".join(chars)


def make_invoice(minimal=False):
    inv_no = f"INV-{random.randint(1000, 9999)}"
    date = f"{random.randint(1,28):02d}/{random.randint(1,12):02d}/{random.choice(['2024','2025','2026'])}"
    company = random.choice(companies)
    total = f"${random.randint(50, 9999)}.{random.randint(0,99):02d}"
    items = random.randint(1, 6)
    header = random.choice(["INVOICE", "Sales Invoice", "Bill", "Tax Invoice"])
    lines = [
        header,
        f"{'Invoice No' if random.random()<0.5 else 'Invoice Number'}: {inv_no}",
        f"Date: {date}",
        f"{'From' if random.random()<0.4 else 'Billed By'}: {company}",
        f"Bill To: {random.choice(names)}",
    ]
    if not minimal:
        lines.append("")
        lines.append("Description        Qty    Price")
        for i in range(items):
            lines.append(f"Item {i+1}               {random.randint(1,5)}      ${random.randint(10,500)}.00")
        lines.append("")
        lines.append(f"Subtotal: ${random.randint(40,9000)}.00")
        lines.append(f"Tax: ${random.randint(1,500)}.00")
    # sometimes omit the word "total" explicitly to make it harder
    if random.random() < 0.85:
        lines.append(f"{'Amount Due' if random.random()<0.5 else 'Total'}: {total}")
    lines.append("Thank you for your business!")
    text = "\n".join(lines)
    return ocr_noise(text)


def make_resume(minimal=False):
    name = random.choice(names)
    email = name.lower().replace(" ", ".") + f"{random.randint(1,99)}@gmail.com"
    phone = f"+92-3{random.randint(0,9)}{random.randint(0,9)}-{random.randint(1000000,9999999)}"
    skills = ", ".join(random.sample(skills_pool, k=5))
    lines = [name, f"Email: {email}", f"Phone: {phone}"]
    if not minimal:
        lines += [
            "",
            random.choice(["EDUCATION", "Academic Background"]),
            "BS Computer Science, 2020 - 2024",
            "",
            random.choice(["EXPERIENCE", "Work History"]),
            f"Intern, {random.choice(companies)} - Worked on data pipelines and reporting tools.",
            f"Junior Developer, {random.choice(companies)} - Built internal dashboards and automation scripts.",
        ]
    lines += ["", f"Skills: {skills}"]
    text = "\n".join(lines)
    return ocr_noise(text)


def make_other():
    text = random.choice(other_topics)
    return ocr_noise(text, level=0.1)


def build_dataset(n_per_class=60):
    rows = []
    for i in range(n_per_class):
        rows.append((make_invoice(minimal=(i % 5 == 0)), "Invoice"))
    for i in range(n_per_class):
        rows.append((make_resume(minimal=(i % 5 == 0)), "Resume"))
    # "Other" pool is smaller/fixed; sample with replacement + light noise
    for _ in range(n_per_class):
        base = make_other()
        rows.append((base, "Other"))
    random.shuffle(rows)
    return rows


if __name__ == "__main__":
    rows = build_dataset(n_per_class=60)
    with open("dataset/documents.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label"])
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to dataset/documents.csv")
