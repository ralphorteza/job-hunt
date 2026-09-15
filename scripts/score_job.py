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

def job_exists(csv_filename, company, role, url):
    csv_path = Path(csv_filename)

    if not csv_path.exists():
        return False

    with open(csv_path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            # Prefer URL comparison when both jobs have one
            if url and row.get("URL"):
                if row["URL"].strip() == url.strip():
                    return True

            # Fallbback to company + role
            same_company = ( row.get("Company", "").strip().lower() == company.strip().lower() )
            same_role = ( row.get("Role", "").strip().lower() == role.strip().lower() )

            if same_company and same_role:
                return True
    return False

def parse_job_file(filename):
    with open(filename, "r", encoding="utf-8" as file:
              content = file.read()

    metadata = {
        "Company": "",
        "Role": "",
        "URL": "",
        "Location": "",
    }

    description_lines = []
    reading_description = False
    
    for line in content.splitlines():
        line = line.strip()

        if line.lower() == "description:":
              reading_description = True
              continue

        if reading_description:
              description_lines.append(line)
              continue

        for key in metadata:
            prefix = f"{key}:"

            if line.lower().startswith(prefix.lower()):
                metadata[key] = line len(prefix):].strip()
                break

    description "\n".join(description_lines)

    return metadata, description

def validate_job(metadata, description):
    required_fields = ["Company", "Role"]

    missing = [
            field
            for field in required_fields
            if not metadata[field]
    ]

    if missing:
        raise ValueError(f"Missing required metadata: {', '.join(missing)}")

    if not description.strip():
        raise ValueError("Job description is empty.")

def save_job(
        csv_filename,
        company,
        role,
        url,
        location,
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
                "URL",
                "Location",
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
            "URL": url,
            "Location": location,
            "Score": score,
            "Resume": resume,
            "Matched Skills": ", ".join(matches),
            "Status": "Interested",
            "Date Added": date.today().isoformat(),
            "Description File": description_file,
        })

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python score_job.py " "<job_description_file>")
        sys.exit(1)

    filename = sys.argv[1]

    try:
        metadata, description = parse_job_file(filename)
        validate_job(metadata, description)
    except FileNotFoundError:
        print(f"Error: File not found: {filename}")
        sys.exit(1)
    except ValueError as error:
        print(f"Error: {error}")
        sys.exit(1)

    company = metadata["Company"]
    role = metadata["Role"]
    url = metadata["URL"]
    location = metadata["Location"]

    raw_score, matches = score_job(description)
    normalize_score = normalize(raw_score)
    resume = choose_resume(description)

    print(f"\nCompany: {company}")
    print(f"Role: {role}")

    if location:
        print(f"Location: {location}")
    if url:
        print(f"URL: {url}")

    print(f"\nRaw score: {raw_score}")
    print(f"Match score: {normalized_score}/10")
    print(f"Reccomended resume: {resume}")

    print("\nMatched skills:")
    for skill in matches:
        print(f"- {skill}")

    csv_filename = "jobs.csv"

    if job_exists(
            csv_filename,
            company,
            role,
            url
    ):
        print("\nJob already exists in jobs.csv")
    else:
        save_job(
                csv_filename,
                company,
                role,
                url,
                location,
                normalize_score,
                resume,
                matches,
                filename
        )

        print("\nJob saved to jobs.csv")
                
