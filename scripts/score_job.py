#!/usr/bin/env python3
import sys
import csv
import re
import json
from datetime import date
from pathlib import Path

# Skill weights:
# 3 = core skill
# 2 = important skill
# 1 = supporting weight
DEFAULT_SKILL_WEIGHT = 1

APPLY_FIT_THRESHOLD = 7.0
APPLY_REQUIRED_THRESHOLD = 70.0

REVIEW_FIT_THRESHOLD = 5.0
REVIEW_REQUIRED_THRESHOLD = 50.0

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

def count_missing_core_skills(comparison, track):
    count = 0
    
    for skill in comparison["required_missing"]:
        if get_skill_weight(skill, track) >= 3:
            count += 1
    
    return count

def build_recommendation_reasons(comparison, fit_score, required_percentage):
    reasons = []
    
    if fit_score >= 8:
        reasons.append("Strong overall skill match")
    elif fit_score >= 6:
        reasons.append("Moderate overall skill match")
    else:
        reasons.append("Low overall skill match")
        
    if required_percentage is not None:
        if required_percentage >= 85:
            reasons.append("Most required skills are covered")
        elif required_percentage >= 70:
            reasons.append("Good coverage of required skills")
        elif required_percentage >= 50:
            reasons.append("Several required skills are missing")
        else:
            reasons.append("Many required skills are missing")
            
    return reasons

def build_skill_warnings(comparison, track):
    warnings = []
    missing_required = comparison["required_missing"]
    
    for skill in missing_required:
        weight = get_skill_weight(skill, track)
        
        if weight >= 3:
            warnings.append(f"Missing core required skill: {skill}")
        else:
            warnings.append(f"Missing required skill: {skill}")
            
    return warnings

def recommend_application(fit_score, required_percentage, missing_core_skills):
    # Some posting don't have a recognizable
    # required-qualifications section.
    if missing_core_skills >= 3:
        return "SKIP"
    
    if missing_core_skills >= 2:
        return "REVIEW"
    
    if required_percentage is None:
        if fit_score >= APPLY_FIT_THRESHOLD:
            return "APPLY"
        
        if fit_score >= REVIEW_FIT_THRESHOLD:
            return "REVIEW"
        
        return "SKIP"
    
    if (
        fit_score >= APPLY_FIT_THRESHOLD
        and required_percentage >= APPLY_REQUIRED_THRESHOLD
    ):
        return "APPLY"
        
    if (
        fit_score >= REVIEW_FIT_THRESHOLD
        and required_percentage >= REVIEW_REQUIRED_THRESHOLD
    ):
        return "REVIEW"
    
    return "SKIP"

def calculate_priority(recommendation, fit_score, required_percentage):
    if recommendation == "SKIP":
        return "LOW"
    
    if (
        recommendation == "APPLY"
        and fit_score >= 8.5
        and (
            required_percentage is None
            or required_percentage >= 85
        )
    ):
        return "HIGH"
    
    if recommendation == "APPLY":
        return "MEDIUM"
    
    return "LOW"

def get_skill_weight(skill, track):
    return SKILL_TRACKS.get(track, {}).get(skill, DEFAULT_SKILL_WEIGHT)

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


def calculate_weighted_match(matched, missing, track):
    matched_wieght = sum(get_skill_weight(skill,track) for skill in missing)
    missing_wieght = sum(get_skill_weight(skill,track) for skill in missing)
    
    total_weight = matched_wieght + missing_wieght
    
    if total_weight == 0:
        return None
    
    return (matched_wieght / total_weight) * 100


def calculate_fit_score(comparison, track):
    required_percentage = calculate_weighted_match(
        comparison["required_matched"],
        comparison["required_missing"],
        track
    )
    preferred_percentage = calculate_weighted_match(
        comparison["preferred_matched"],
        comparison["preferred_missing"],
        track
    )
    general_percentage = calculate_weighted_match(
        comparison["general_matched"],
        comparison["general_missing"],
        track
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
        
    if weighted_total == 0:
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
            row_url = row.get("URL", "").strip()
            
            # If both have URLs, URL is authoritative
            if url and row_url:
                if row_url == url.strip():
                    return True
                
                # Different URLS = different postings.
                continue
            
            same_company = (
                row.get("Company", "")
                .strip()
                .lower()
                == company.strip().lower()
            )
            
            same_role = (
                row.get("Role", "")
                .strip()
                .lower()
                == role.strip().lower()
            )
            
            if same_company and same_role:
                return True
        # for row in reader:
        #     # Prefer URL comparison when both jobs have one
        #     if url and row.get("URL"):
        #         if row["URL"].strip() == url.strip():
        #             return True

        #     # Fallbback to company + role
        #     same_company = ( row.get("Company", "").strip().lower() == company.strip().lower() )
        #     same_role = ( row.get("Role", "").strip().lower() == role.strip().lower() )

        #     if same_company and same_role:
        #         return True
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
    track,
    track_score,
    fit_score,
    required_percentage,
    preferred_percentage,
    recommendation,
    priority,
    missing_required,
    resume,
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
                "Job Track",
                "Track Score",
                "Fit Score",
                "Required Match %",
                "Preferred Match %",
                "Recommendation",
                "Priority",
                "Missing Required Skills",
                "Resume",
                "Status",
                "Date Added",
                "Description File",
        ]

        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        # required_matches = [
        #     match["skill"]
        #     for match in matches
        #     if match["section"] == "required"
        # ]
        
        # preferred_matches = [
        #     match["skill"]
        #     for match in matches
        #     if match["section"] == "preferred"
        # ]
        
        # general_matches = [
        #     match["skill"]
        #     for match in matches
        #     if match["section"] == "general"
        # ]
        
        writer.writerow({
            "Company": company,
            "Role": role,
            "URL": url,
            "Location": location,
            "Track Score": track_score,
            "Fit Score": fit_score,
            
            "Required Match %": (
                round(required_percentage)
                if required_percentage is not None
                else ""
            ),
            "Preferred Match %": (
                round(preferred_percentage)
                if preferred_percentage is not None
                else ""
            ),
            "Recommendation": recommendation,
            "Priority": priority,
            
            "Missing Required Skills": ", ".join(missing_required),
            
            "Resume": resume,
            "Status": "Interested",
            "Date Added": date.today().isoformat(),
            "Description File": description_file,
        })
        
def process_job(filename):
    metadata, description = parse_job_file(filename)
    validate_job(metadata, description)
    
    company = metadata["Company"]
    role = metadata["Role"]
    url = metadata["URL"]
    location = metadata["Location"]
    
    # determine the job track
    results = score_job(description)
    results = normalize_results(results)
    
    resume = choose_resume(results)
    track_score = results[resume]["score"]
    
    # Load candidate profile
    profile = load_profile("config/profile.json")
    validate_profile(profile)
    
    # Compare candidate against job
    job_skills = extract_job_skills(description)
    comparison = compare_profile(job_skills, profile)
    
    required_percentage = calculate_weighted_match(
        comparison["required_matched"],
        comparison["required_missing"],
        resume
    )
    preferred_percentage = calculate_weighted_match(
        comparison["preferred_matched"],
        comparison["preferred_missing"],
        resume
    )
    general_percentage = calculate_weighted_match(
        comparison["general_matched"],
        comparison["general_missing"],
        resume
    )
    
    fit_score = calculate_fit_score(comparison, resume)
    missing_core_skills = count_missing_core_skills(comparison, resume)
    
    recommendation = recommend_application(
        fit_score,
        required_percentage,
        missing_core_skills
    )
    
    priority = calculate_priority(
        recommendation,
        fit_score,
        required_percentage
    )
    
    return {
        "company": company,
        "role": role,
        "url": url,
        "location": location,
        
        "track": resume,
        "track_score": track_score,
        "resume": resume,
        
        "fit_score": fit_score,
        
        "required_percentage": required_percentage,
        "preferred_percentage": preferred_percentage,
        "general_percentage": general_percentage,
        
        "required_matched": comparison["required_matched"],
        "required_missing": comparison["required_missing"],
        
        "preferred_matched": comparison["preferred_matched"],
        "preferred_missing": comparison["preferred_missing"],
        
        "missing_core_skills": missing_core_skills,
        "recommendation": recommendation,
        "priority": priority,
        
        "description_file": str(filename),
    }
    

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python score_job.py " "<job_description_file>")
        sys.exit(1)

    filename = sys.argv[1]

    # 2. Parse job description file
    try:
        job = process_job(filename)
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

    # 3. Classify the job
    results = score_job(description)
    results = normalize_results(results)
    
    resume = choose_resume(results)
    
    normalized_score = results[resume]["score"]
    matches = results[resume]["matches"]
    
    # 4. Load candidate profile
    try:
        profile = load_profile("config/profile.json")
        validate_profile(profile)
    except FileNotFoundError:
        print("Error: config/profile.json was not found.")
        sys.exit(1)
    except ValueError as error:
        print(f"Profile error: {error}")
        sys.exit(1)
    
    # 5. Extract skills requested by employer
    job_skills = extract_job_skills(description)
    
    # 6. Compare job against candidate profile
    comparison = compare_profile(job_skills, profile)
    
    # 7. Calculate weighted match percentages
    required_percentage = calculate_weighted_match(
        comparison["required_matched"],
        comparison["required_missing"],
        resume
    )
    
    preferred_percentage = calculate_weighted_match(
        comparison["preferred_matched"],
        comparison["preferred_missing"],
        resume
    )
    
    general_percentage = calculate_weighted_match(
        comparison["general_matched"],
        comparison["general_missing"],
        resume
    )
    print("\nCandidate fit:")
    
    # 8. Calculate overall fit
    fit_score = calculate_fit_score(comparison, resume)
    
    # 9. Detect missing core skills
    missing_core_skills =count_missing_core_skills(comparison, resume) 
    
    # 10. Generate application recommendation
    recommendation = recommend_application(
        fit_score,
        required_percentage,
        missing_core_skills
    )
    
    priority = calculate_priority(
        recommendation,
        fit_score,
        required_percentage
    )
    
    reasons = build_recommendation_reasons(
        comparison,
        fit_score,
        required_percentage
    )
    
    warnings = build_skill_warnings(
        comparison,
        resume
    )
    
    # 11. Print basic job information
    print("\n" + "=" * 50)
    print("JOB")
    print("=" * 50)
    
    print(f"Company:   {company}")
    print(f"Role:      {role}")
    
    if location:
        print(f"Location:  {location}")
    if url:
        print(f"URL:       {url}")
    
    # 12. Print Job classification
    print("\nTrack scores:")
    
    for track, result in results.items():
        print(
            f"   {track:<15} "
            f"{result['score']}/10 "
            f"(raw: {result['raw_score']:.1f})"
        )
    
    print(f"\nRecommended resume: {resume}")
    
    # 13. Print matched job skills
    print("\nMatched skills:")
    for match in matches:
        print(
            f"- {match['skill']:<20} "
            f"[{match['section']}] "
            f"+{match['weighted_score']:.1f}"
        )    
    
    # 14. Print candidate fit
    print("\n" + "=" * 50)
    print("CANDIDATE FIT")
    print("=" * 50)
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
        
    if general_percentage is not None:
        print(
            f"General match: "
            f"{general_percentage:.0f}%"
        )
    else:
        print("General match: N/A")
    
    print(f"\nOverall fit: {fit_score}/10")
    
    # 15. Print required skills
    print("\nRequired skills matched:")
    
    if comparison["required_matched"]:    
        for skill in comparison["required_matched"]:
            weight = get_skill_weight(skill, resume)
            print(
                f" ✓ {skill}"
                f"weight: {weight}"
            )
    else:
        print("  None")
        
    print("\nRequired skills missing:")
    if comparison["required_missing"]:
        for skill in comparison["required_missing"]:
            weight = get_skill_weight(skill, resume)
            print(
                f" ✗ {skill}"
                f"weight: {weight}"
            )
    else:
        print("  None")
    
    # 16. Print preferred skills
    print("\nPreferred skills matched:")
    if comparison["preferred_matched"]:
        for skill in comparison["preferred_matched"]:
            print(f" ✓ {skill}")
    else:
        print("  None")
    
    print("\nPreferred skills missing:")
    if comparison["preferred_missing"]:                    
        for skill in comparison["preferred_missing"]:
            print(f" - {skill}")
    else:
        print("  None")
        
    # 17. Print final recommendation
    print("\n" + "=" * 50)
    print("APPLICATION RECOMMENDATION")
    print("=" * 50)
    
    print(f"Priority:           {priority}")
    print(f"Resume:             {resume}")
    print(f"Overall fit:        {fit_score}/10")
    
    if required_percentage is not None:
        print(
            f"Required match: "
            f"{required_percentage:.0f}%"
        )
        
    if preferred_percentage is not None:
        print(
            f"Preferred match: "
            f"{preferred_percentage:.0f}%"
        )
        
    # 18. Print reasons
    print("\nWhy:")
    for reason in reasons:
        print(f"  ✓ {reason}")
        
    # 19. Print warnings
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  ! {warning}")
    
    
    print("\nTrack scores:")
    for track, result in results.items():
        print(
            f"  {track:<15} "
            f"{result['score']}/10 "
            f"(raw: {result['raw_score']})"
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
            resume,
            normalized_score,
            fit_score,
            required_percentage,
            preferred_percentage,
            recommendation,
            priority,
            comparison["required_missing"],
            resume,
            filename
        )

        print("\nJob saved to jobs.csv")
                
