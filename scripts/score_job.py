#!/usr/bin/env python3
import sys
import csv
from datetime import date
from pathlib import Path

SKILLS = {
        "c++": 3,
        "c/c++": 3,
        "embedded linux": 3,
        "linux": 2,
        "stm32": 3,
        "microcontroller": 2,
        "spi": 2,
        "i2c": 2,
        "uart": 2,
        "python": 1,
        "real-time": 3,
        "rtos": 3,
        "pid": 3,
        "foc": 3,
        "bldc": 3,
        "pmsm": 3,
        "react": 2,
        "node.js": 2
}

TARGET_SKILLS = [
        "c++",
        "linux",
        "stm32",
        "microcontroller",
        "spi",
        "i2c",
        "uart",
        "rtos",
        "real-time",
        "python",
        "foc",
        "pid",
        "bldc",
        "pmsm",
]


def find_missing_skills(description):
    text = description.lower()
    return [skill
            for skill in TARGET_SKILLS
            if skill not in text
    ]
def score_job(description):
    text = description.lower()
    score = 0
    matches = []

    for skill, weight in SKILLS.items():
        if skill in text:
            score += weight
            matches.append(skill)

    return score, matches

def normalize(score):
    if score >= 18:
        return 10
    elif score >= 15:
        return 9
    elif score >= 12:
        return 8
    elif score >= 9:
        return 7
    elif score >= 6:
        return 6
    else:
        return 4

def choose_resume(description):
    text = description.lower()

    motor_terms = [
            "foc",
            "bldc",
            "pmsm",
            "motor control",
            "pid"
            ]

    embedded_terms = [
            "firmware",
            "stm32",
            "microcontroller",
            "rtos",
            "embedded"
            ]

    if any(term in text for term in motor_terms):
        return "motor_control"

    if any(term in text for term in embedded_terms):
        return "embedded"

    return "swe"

def job_exists(csv_filename, company, role):
    csv_path = Path(csv_filename)
    if not csv_path.exists():
        return False

    with open(csv_path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            same_company = (
                    row["Company"].strip().lower() == company.strip().lower()
            )

            same_role = (
                    row["Role"].strip().lower() == role.strip().lower()
            )

            if same_company and same_role:
                return True
    return False

def save_job(
        csv_filename,
        company,
        role,
        score,
        resume,
        matches,
        description_file
):
    csv_path = Path(csv_filename)

    # Check whether the CSV already exist.
    # Else, we'll need to write the header.
    file_exists = csv_path.exists()

    with open(csv_path, "a", newline="", encoding="utf-8") as file:
        fieldnames = [
                "Company",
                "Role",
                "Score",
                "Resume",
                "Matched Skills",
                "Status",
                "Date Added",
                "Description File"
        ]

        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "Company": company,
            "Role": role,
            "Score": score,
            "Resume": resume,
            "Matched Skills": ", ".join(matches),
            "Status": "Interested",
            "Date Added": date.today().isoformat(),
            "Description File": description_file,
        })

if __name__ == "__main__":
    '''    description = """
    We are looking for an embedded firmware engineer experienced with stm32, c++, spi, i2c, linux, and real-time systems.
    """
    '''
    if len(sys.argv) != 4:
        print("Usage: python score_job.py "
              "<job_description_file> <company> <role>"
        )
        sys.exit(1)
    
    filename = sys.argv[1]
    company = sys.argv[2]
    role = sys.argv[3]

    with open(filename, "r", encoding="utf-8") as file:
        description = file.read()

    raw_score, matches = score_job(description)
    normalize_score = normalize(raw_score)
    resume = choose_resume(description)
    missing = find_missing_skills(description)

    print("\nMatched skills:")
    for skill in matches:
        print(f"- {skill}")
    """
    print("\nMissing skills:")
    for skill in missing:
        print(f"- {skill}")
    """
    print(f"Raw score: {raw_score}")
    print(f"Match score: {normalize_score}/10")
    print(f"Skills matched: {matches}")
    print(f"Reccomended resume: {resume}")

    print("\nMatched skills:")
    for skill in matches:
        print(f"- {skill}")

    csv_filename = "jobs.csv"

    if job_exists(csv_filename, company, role):
        print("\nJob already exists in jobs.csv")
    else:
        save_job(
                csv_filename,
                company,
                role,
                normalize_score,
                resume,
                matches,
                filename
        )

        print("\nJob saved to jobs.csv")
