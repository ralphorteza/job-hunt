#!/usr/bin/env python3
import sys
import csv
import re
import json
from datetime import date
from pathlib import Path

REQUIRED_HEADINGS = [
    "requirements",
    "required qualifications",
    "minimum qualifications",
    "basic qualifications",
    "what you need"
    "what we're looking for",
    "what we are looking for",
]

PREFERRED_HEADINGS = [
    "preferred qualifications",
    "preferred sklls",
    "nice to have",
    "nice-to-have",
    "bonus qualifications",
    "bonus points",
    "desired qualifications",
]

GENERAL_HEADINGS = [
    "responsibilities",
    "what you'll do",
    "what you will do",
    "about the role",
    "the role",
    "job description",
]

SECTION_WEIGHTS = {
    "required": 1.5,
    "general": 1.0,
    "preferred": 0.5,
}

SKILL_PATTERNS = {
    "c": [
        r"(?<![\w+])c(?![\w+])",
        r"(?<!\w)c(?=\s*/\s*c\+\+)",
    ],
    "c++": [
        r"(?<!\w)c\+\+(?!\w)",
        r"(?<!\w)c\s*/\s*c\+\+(?!\w)",
    ],
    "embedded linux": [
        r"\bembedded\s+linux\b",
    ],

    "linux": [
        r"\blinux\b",
    ],

    "firmware": [
        r"\bfirmware\b",
    ],

    "embedded": [
        r"\bembedded\b",
    ],

    "stm32": [
        r"\bstm32\w*\b",
    ],

    "microcontroller": [
        r"\bmicrocontrollers?\b",
        r"\bmcus?\b",
    ],

    "rtos": [
        r"\brtos\b",
        r"\bfreertos\b",
        r"\breal[\s-]+time\s+operating\s+systems?\b",
    ],

    "real-time": [
        r"\breal[\s-]+time\b",
    ],

    "spi": [
        r"\bspi\b",
    ],

    "i2c": [
        r"\bi2c\b",
        r"\bi²c\b",
    ],

    "uart": [
        r"\buart\b",
    ],

    "can": [
        r"\bcan\s+bus\b",
        r"\bcan\b",
    ],

    "python": [
        r"\bpython\b",
    ],

    "java": [
        r"\bjava\b",
    ],

    "javascript": [
        r"\bjavascript\b",
    ],

    "typescript": [
        r"\btypescript\b",
    ],

    "react": [
        r"\breact(?:\.js|js)?\b",
    ],

    "node.js": [
        r"\bnode(?:\.js|js)\b",
    ],

    "git": [
        r"\bgit\b",
    ],

    "github actions": [
        r"\bgithub\s+actions\b",
    ],

    "ci/cd": [
        r"\bci\s*/\s*cd\b",
        r"\bcontinuous\s+integration\b",
        r"\bcontinuous\s+delivery\b",
        r"\bcontinuous\s+deployment\b",
    ],

    "pid": [
        r"\bpid\b",
        r"\bproportional[\s-]+integral[\s-]+derivative\b",
    ],

    "foc": [
        r"\bfoc\b",
        r"\bfield[\s-]+oriented\s+control\b",
    ],

    "bldc": [
        r"\bbldc\b",
        r"\bbrushless\s+dc\b",
    ],

    "pmsm": [
        r"\bpmsm\b",
        r"\bpermanent\s+magnet\s+synchronous\s+motors?\b",
    ],

    "pwm": [
        r"\bpwm\b",
        r"\bpulse[\s-]+width\s+modulation\b",
    ],

    "oscilloscope": [
        r"\boscilloscopes?\b",
    ],

    "gate driver": [
        r"\bgate\s+drivers?\b",
    ],

    "device driver": [
        r"\bdevice\s+drivers?\b",
    ],

    "bare metal": [
        r"\bbare[\s-]+metal\b",
    ],
    "motor control": [
        r"\bmotor\s+control\b"
    ]
}

SKILL_TRACKS = {
    "embedded": {
        # "c": 2,
        "c++": 3,
        "firmware": 3,
        "embedded": 3,
        "embedded linux": 3,
        "linux": 2,
        "stm32": 3,
        "microcontroller": 3,
        "rtos": 3,
        "real-time": 2,
        "spi": 2,
        "i2c": 2,
        "uart": 2,
        "can": 2,
        "device driver": 2,
        "baremetal": 3,
    },
    "motor_control": {
        "c":2,
        "c++":3,
        "firmware": 2,
        "embedded": 2,
        "real-time": 3,
        "microcontroller": 2,
        "motor control": 4,
        "foc": 4,
        "field oriented control": 4,
        "pid": 3,
        "bldc": 4,
        "pmsm": 4,
        "pwm": 2,
        "encoder": 2,
        "gate driver": 3,
        "oscilloscope": 2,
    },
    "swe": {
        "python": 3,
        "java": 3,
        "javascript": 3,
        "typescript": 3,
        "react": 3,
        "node.js": 3,
        "linux": 1,
        "git": 2,
        "ci/cd": 2,
        "github actions": 2,
        "pytest": 2,
        "api": 2,
        "rest": 2,
    },
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

def extract_job_skills(description):
    sections = split_job_sections(description)
    job_skills = []
    
    for skill in SKILL_PATTERNS:
        section = find_skill_section(skill, sections)
        
        if section is not None:
            job_skills.append({
                "skill": skill,
                "section": section,
            })
            
    return job_skills

def compare_profile(job_skills, profile):
    candidate_skills = {skill.lower() for skill in profile["skills"]}
    
    results = {
        "required_matched": [],
        "required_missing": [],
        "preferred_matched": [],
        "preferred_missing": [],
        "general_matched": [],
        "general_missing": [],
    }
    
    for item in job_skills:
        skill = item["skill"]
        section = item["section"]
        
        has_skill = skill.lower() in candidate_skills
        
        if section == "required":
            if has_skill:
                results["required_matched"].append(skill)
            else:
                results["required_missing"].append(skill)
        elif section == "preferred":
            if has_skill:
                results["preferred_matched"].append(skill)
            else:
                results["preferred_missing"].append(skill)
        else:
            if has_skill:
                results["general_matched"].append(skill)
            else:
                results["general_missing"].append(skill)
    return results


def calculate_match_percentage(matched, missing):
    total = len(matched) + len(missing)
    
    if total == 0:
        return None
    
    return (len(matched) / total) * 100


def calculate_fit_score(comparison):
    required_percentage = calculate_match_percentage(
        comparison["required_matched"],
        comparison["required_missing"]
    )
    preferred_percentage = calculate_match_percentage(
        comparison["preferred_matched"],
        comparison["preferred_missing"]
    )
    general_percentage = calculate_match_percentage(
        comparison["general_matched"],
        comparison["general_missing"]
    )
    
    weighted_total = 0
    total_weight = 0
    
    if required_percentage is not None:
        weighted_total += required_percentage * 0.65
        total_weight += 0.65

    if preferred_percentage is not None:
        weighted_total += preferred_percentage * 0.20
        total_weight += 0.20

    if general_percentage is not None:
        weighted_total += general_percentage * 0.15
        total_weight += 0.15
        
    if total_weight == 0:
        return 0
    
    percentage = weighted_total / total_weight
    return round(percentage / 10, 1)
        
def load_profile(filename):
    with open(filename, "r", encoding="utf-8") as file:
        profile = json.load(file)
        
    return profile

def validate_profile(profile):
    if "skills" not in profile:
        raise ValueError("profile.json is missing the 'skills' field.")
    
    if not isinstance(profile["skills"], list):
        raise ValueError("'skills' in profile.json must be a list.")

def detect_section(line):
    heading = line.strip().lower().rstrip(":")
    
    if heading in REQUIRED_HEADINGS:
        return "required"
    
    if heading in PREFERRED_HEADINGS:
        return "preferred"
    
    if heading in GENERAL_HEADINGS:
        return "general"
    
    return None


def find_skill_section(skill, sections):
    if skill_matches(skill, sections["required"]):
        return "required"
    
    if skill_matches(skill, sections["general"]):
        return "general"
    
    if skill_matches(skill, sections["preferred"]):
        return "preferred"
    
    return None

def split_job_sections(description):
    sections = {
        "required": [],
        "preferred": [],
        "general": [],
    }
    
    current_section = "general"
    
    for line in description.splitlines():
        detected = detect_section(line)
        
        if detected:
            current_section = detected
            continue
        
        sections[current_section].append(line)
        
    return {
        section: "\n".join(lines)
        for section, lines in sections.items()
    }

def find_missing_skills(description):
    text = description.lower()
    return [skill
            for skill in TARGET_SKILLS
            if skill not in text
    ]
      
def skill_matches(skill, text):
    patterns = SKILL_PATTERNS.get(skill, [])
    
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False

def score_job(description):
    sections = split_job_sections(description)
    
    results = {}
    
    for track, skills in SKILL_TRACKS.items():
        raw_score = 0
        matches = []
        
        for skill, weight in skills.items():
            section = find_skill_section(skill, sections)
            
            if section is None:
                continue
            
            multiplier = SECTION_WEIGHTS[section]
            weighted_score = weight * multiplier
            raw_score += weighted_score
            
            matches.append({
                "skill": skill,
                "section": section,
                "base_weight": weight,
                "weighted_score": weighted_score,
            })
            
        results[track] = {
            "raw_score": raw_score,
            "matches": matches,
        }
    return results

# def score_job(description):
#     # text = description.lower()
    
#     results = {}
    
#     for track, skills, in SKILL_TRACKS.items():
#         raw_score = 0
#         matches = []
        
#         # for skill, weight in skills.items():
#         #     if skill in text:
#         #         raw_score += weight
#         #         matches.append(skill)
#         for skill, weight in skill.items():
#             if skill_matches(skill, text):
#                 raw_score += weight
#                 matches.append(skill)
                
#         results[track] = {
#             "raw_score": raw_score,
#             "matches": matches,
#         }
        
#     return results

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
    

def normalize_results(results):
    for track in results:
        raw_score = results[track]["raw_score"]
        
        results[track]["score"] = normalize(raw_score)
    
    return results  


def choose_resume(results):
    best_track = max(results, key=lambda track: results[track]["raw_score"])
    return best_track

# def choose_resume(description):
#     text = description.lower()


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
    with open(filename, "r", encoding="utf-8") as file:
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
                metadata[key] = line[len(prefix):].strip()
                break

    description = "\n".join(description_lines)

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
                "Required Matches",
                "Preferred Matches",
                "General Matches",
                "Status",
                "Date Added",
                "Description File"
        ]

        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        required_matches = [
            match["skill"]
            for match in matches
            if match["section"] == "required"
        ]
        
        preferred_matches = [
            match["skill"]
            for match in matches
            if match["section"] == "preferred"
        ]
        
        general_matches = [
            match["skill"]
            for match in matches
            if match["section"] == "general"
        ]
        
        writer.writerow({
            "Company": company,
            "Role": role,
            "URL": url,
            "Location": location,
            "Score": score,
            "Resume": resume,

            "Required Matches": ", ".join(required_matches),
            "Preferred Matches": ", ".join(preferred_matches),
            "General Matches": ", ".join(general_matches),
            
            "Status": "Interested",
            "Date Added": date.today().isoformat(),
            "Description File": description_file,
        })
        

if __name__ == "__main__":
    # test_text = """
    # We're looking for an engineer experienced with c/c++, FreeRTOS, STM32 microcontrollers, real-time firmware,
    # SPI, I2C and UART.
    # """
    
    # for skill in SKILL_PATTERNS:
    #     if skill_matches(skill, test_text):
    #         print(skill)
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

    profile = load_profile("config/profile.json")
    validate_profile(profile)
    
    job_skills = extract_job_skills(description)
    
    comparison = compare_profile(job_skills, profile)
    fit_score = calculate_fit_score(comparison)
    
    required_percentage = calculate_match_percentage(
        comparison["required_matched"],
        comparison["required_missing"]
    )
    
    preferred_percentage = calculate_match_percentage(
        comparison["preferred_matched"],
        comparison["preferred_missing"]
    )
    
    print("\nCandidate fit:")
    
    if required_percentage is not None:
        print(
            f"Required match: "
            f"{required_percentage:.0f}%"
        )
    else:
        print("Required match: N/A")
        
    if preferred_percentage is not None:
        print(
            f"Preferred match: "
            f"{preferred_percentage:.0f}%"
        )
    else:
        print("Preferred match: N/A")
    
    print(f"\nOverall fit: {fit_score}/10")
    
    
    print("\nRequired skills matched:")
    for skill in comparison["required_matched"]:
        print(f" ✓ {skill}")
        
    print("\nRequired skills missing:")
    for skill in comparison["required_missing"]:
        print(f" ✗ {skill}")
        
    print("\nPreferred skills matched:")
    for skill in comparison["preferred_matched"]:
        print(f" ✓ {skill}")
        
    print("\nPreferred skills missing:")
    for skill in comparison["preferred_missing"]:
        print(f" - {skill}")
        
    company = metadata["Company"]
    role = metadata["Role"]
    url = metadata["URL"]
    location = metadata["Location"]

    results = score_job(description)
    results = normalize_results(results)
    
    resume = choose_resume(results)
    
    normalized_score = results[resume]["score"]
    matches = results[resume]["matches"]

    print(f"\nCompany: {company}")
    print(f"Role: {role}")

    if location:
        print(f"Location: {location}")
    if url:
        print(f"URL: {url}")

    print("\nTrack scores:")
    for track, result in results.items():
        print(
            f"  {track:<15} "
            f"{result['score']}/10 "
            f"(raw: {result['raw_score']})"
        )
        
    
    # print(f"\nRaw score: {raw_score}")
    # print(f"Match score: {normalize_score}/10")
    print(f"Reccomended resume: {resume}")

    print("\nMatched skills:")
    # for skill in matches:
    #     print(f"- {skill}")
    for match in matches:
        print(
            f"- {match['skill']:<20} "
            f"[{match['section']}] "
            f"+{match['weighted_score']:.1f}"
        )
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
                normalized_score,
                resume,
                matches,
                filename
        )

        print("\nJob saved to jobs.csv")
                
