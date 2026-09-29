#!/usr/bin/env python3
import sys
import csv
import re
import json
from datetime import date
from pathlib import Path
from url_utils import normalize_url
# Skill weights:
# 3 = core skill
# 2 = important skill
# 1 = supporting weight
DEFAULT_SKILL_WEIGHT = 1

APPLY_FIT_THRESHOLD = 7.0
APPLY_REQUIRED_THRESHOLD = 70.0

REVIEW_FIT_THRESHOLD = 5.0
REVIEW_REQUIRED_THRESHOLD = 50.0

RELATED_DEGREE_FIELDS = {
    "computer science": {
        "computer engineering",
        "software engineering",
    },
    "computer engineering": {
        "computer science",
        "electrical engineering",
        "software engineering",
    },
    "electrical engineering": {
        "computer science",
        "computer engineering",
    },
    "software engineering": {
        "computer science",
        "computer engineering",
    },
}


REQUIRED_HEADINGS = [
    "requirements",
    "required qualifications",
    "minimum qualifications",
    "basic qualifications",
    "what you need",
    "what we're looking for",
    "what we are looking for",
]

PREFERRED_HEADINGS = [
    "preferred qualifications",
    "preferred skills",
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

SKILL_ALIASES = {
    # Embedded / firmware
    "freertos": "rtos",
    "free rtos": "rtos",
    
    "baremetal": "bare metal",
    "bare-metal": "bare metal",
    
    "microcontrollers": "microcontroller",
    "mcu": "microcontroller",
    "mcus": "microcontroller",
    
  # Languages
    "cpp": "c++",
    "cplusplus": "c++",

    "js": "javascript",
    "nodejs": "node.js",
    "node js": "node.js",

    "ts": "typescript",

    # Development
    "github actions": "github actions",
    "github-actions": "github actions",

    "ci cd": "ci/cd",
    "cicd": "ci/cd",

    # Motor control
    "field oriented control": "foc",
    "field-oriented control": "foc",

    "brushless dc": "bldc",

    "permanent magnet synchronous motor": "pmsm",
    "permanent magnet synchronous motors": "pmsm",
    
}

RELATED_SKILLS = {
    "microcontroller": {
        "stm32": 0.90,
        "esp32": 0.90,
        "nrf52": 0.90,
    },

    "motor control": {
        "foc": 0.90,
        "bldc": 0.80,
        "pmsm": 0.80,
    },

    "linux": {
        "embedded linux": 0.90,
    },

    "testing": {
        "pytest": 0.80,
    },
}

SKILL_PATTERNS = {
    "c": [
        r"(?<![\w+])c(?![\w+])",
        r"(?<!\w)c(?=\s*/\s*c\+\+)",
    ],
    "c++": [
        r"(?<!\w)c\+\+(?:\d+)?(?!\w)",
        r"(?<!\w)c\s*/\s*c\+\+(?:\d+)?(?!\w)",
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
        r"\bcan[-\s]?fd\b",
        r"\bcontroller\s+area\s+network\b",
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
        "bare metal": 3,
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

DEGREE_LEVELS = {
    "high_school": 1,
    "associates": 2,
    "bachelors": 3,
    "masters": 4,
    "phd": 5,
}


# def count_missing_core_skills(comparison, track):
#     count = 0
    
#     for skill in comparison["required_missing"]:
#         if get_skill_weight(skill, track) >= 3:
#             count += 1
    
#     return count
def count_missing_core_skills(
    comparison,
    track,
):
    missing_score = 0.0
    
    skill_credits = comparison.get(
        "skill_credits",
        {},
    )
    
    required_skills = (
        comparison["required_matched"]
        + comparison["required_missing"]
    )
    
    for skill in required_skills:
        weight = get_skill_weight(
            skill,
            track,
        )
        
        if weight < 3:
            continue
        
        credit = skill_credits.get(
            skill,
            1.0
            if skill in comparison["required_matched"]
            else 0.0,
        )
        
        if credit >= 0.8:
            continue
        
        if credit > 0.0:
            missing_score += 0.5
        else:
            missing_score += 1.0
            
    return missing_score

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

def count_critical_missing_qualifications(
    qualification_comparison,
    experience_gap_severity="unknown",
):
    critical_count = 0
    
    for qualification in qualification_comparison["required_missing"]:
        qualification_type = qualification["type"]
        
        # Experience requirements have their own severity model.
        # Only a large experience gap counts as critical.
        if qualification_type == "years_experience":
            if experience_gap_severity == "large":
                critical_count += 1
                
            continue
        
        # A missing required degree is critical.
        if qualification_type == "degree":
            critical_count += 1
            
    return critical_count

def recommend_application(
    fit_score,
    required_percentage,
    missing_core_skills,
    required_qualification_percentage,
    critical_missing_qualifications,
    experience_gap_severity,
):
    if experience_gap_severity == "large":
        return "SKIP"
    
    if experience_gap_severity == "moderate":
        return "REVIEW"
    
    # Critical required qualifications are strong blockers.
    if critical_missing_qualifications >= 2:
        return "SKIP"

    if critical_missing_qualifications == 1:
        return "REVIEW"

    # Missing core technical requirements.
    if missing_core_skills >= 3:
        return "SKIP"

    if missing_core_skills >= 2:
        return "REVIEW"

    # Required non-skill qualifications.
    if (
        required_qualification_percentage is not None
        and required_qualification_percentage < 50
    ):
        return "SKIP"

    if (
        required_qualification_percentage is not None
        and required_qualification_percentage < 75
    ):
        return "REVIEW"

    # Posting has no recognizable required-skill section.
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


def calculate_priority(
    recommendation,
    fit_score,
    required_percentage,
    experience_gap_severity="unknown",
):
    if recommendation == "SKIP":
        return "LOW"

    # Large experience gaps should never receive
    # high or medium application priority.
    if experience_gap_severity == "large":
        return "LOW"

    if recommendation == "APPLY":
        if (
            fit_score >= 8.5
            and (
                required_percentage is None
                or required_percentage >= 85
            )
            and experience_gap_severity in (
                "none",
                "unknown",
            )
        ):
            return "HIGH"

        return "MEDIUM"

    if recommendation == "REVIEW":
        if (
            fit_score >= 7.0
            and (
                required_percentage is None
                or required_percentage >= 70
            )
            and experience_gap_severity in (
                "none",
                "small",
                "moderate",
                "unknown",
            )
        ):
            return "MEDIUM"

        return "LOW"

    return "LOW"

def get_candidate_experience_years(profile, domain):
    experience = profile.get("experience", {})
    
    if domain == "embedded":
        return experience.get(
            "embedded_years",
            experience.get("software_years", 0)
        )
    
    return experience.get("software_years", 0)

def detect_experience_domain(text):
    text = text.lower()
    
    embedded_patterns = [
        r"\bembedded\b",
        r"\bfirmware\b",
        r"\bmicrocontroller\b",
        r"\breal[\s-]+time\b",
    ]
    
    for pattern in embedded_patterns:
        if re.search(pattern, text):
            return "embedded"
        
    return "software"

def extract_degree_requirements(text):
    requirements = []
    
    degree_patterns = [
        (
            "phd",
            r"\b(?:ph\.?d\.?|doctorate|doctoral degree)\b",
        ),
        (
            "masters",
            r"\b(?:master'?s?\s+degree|m\.?s\.?)\b",
        ),
        (
            "bachelors",
            r"\b(?:bachelor'?s?\s+degree|b\.?s\.?|b\.?a\.?)\b",
        ),
        (
            "associates",
            r"\bassociate'?s?\s+degree\b",
        ),
    ]
    
    for degree_level, pattern in degree_patterns:
        for match in re.finditer(
            pattern,
            text,
            re.IGNORECASE,
        ):
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 200)
            
            context = text[start:end]
            
            equivalent_experience = bool(
                re.search(
                    r"\bor\s+(?:equivalent|comparable)"
                    r"(?:\s+work)?\s+experience\b",
                    context,
                    re.IGNORECASE,
                )
            )
            
            fields = extract_degree_fields(context)
            related_field_allowed = (
                allows_related_degree_field(context)
            )
            
            requirements.append({
                "type": "degree",
                "value": degree_level,
                "minimum": degree_level,
                "fields": fields,
                "related_field_allowed": (
                    related_field_allowed
                ),
                "equivalent_experience": (
                    equivalent_experience
                ),
                "text": match.group(0),
            })
            
    return requirements

def extract_experience_requirements(text):
    patterns = [
        # 3-5 years / 3–5 years / 3 to 5 years
        (
            r"(?P<minimum>\d+)\s*"
            r"(?:-|–|—|to)\s*"
            r"(?P<maximum>\d+)\s*"
            r"years?\s+of\s+experience"
            r"(?P<context>.{0,100})"
        ),

        # at least 3 years of experience
        (
            r"at\s+least\s+"
            r"(?P<minimum>\d+)\s*"
            r"years?\s+of\s+experience"
            r"(?P<context>.{0,100})"
        ),

        # minimum of 3 years of experience
        (
            r"minimum\s+of\s+"
            r"(?P<minimum>\d+)\s*"
            r"years?\s+of\s+experience"
            r"(?P<context>.{0,100})"
        ),

        # 3 or more years of experience
        (
            r"(?P<minimum>\d+)\s+"
            r"or\s+more\s+"
            r"years?\s+of\s+experience"
            r"(?P<context>.{0,100})"
        ),

        # Existing forms: 3+ years / 3 years
        (
            r"(?P<minimum>\d+)\s*\+?\s*"
            r"years?\s+of\s+experience"
            r"(?P<context>.{0,100})"
        ),
    ]
    
    requirements = []
    matched_spans = []
    
    for pattern in patterns:
        for match in re.finditer(
            pattern,
            text,
            re.IGNORECASE,
        ):
            
            # Don't let a generic pattern match text that
            # was already captured by a more specific pattern.
            start, end = match.span()
            
            overlaps = any(
                start < existing_end
                and end > existing_start
                for existing_start, existing_end
                in matched_spans
            )
            
            if overlaps:
                continue
            
            minimum = int(match.group("minimum"))
            
            maximum_group = match.groupdict().get("maximum")
            
            maximum = (
                int(maximum_group)
                if maximum_group
                else None
            )
            
            matched_text = match.group(0).strip()
            
            requirements.append({
                # Keep "value" for backwards compatibility with existing code/tests.
                "type": "years_experience",
                "value": minimum,
                
                # New representation.
                "minimum": minimum,
                "maximum": maximum,
                
                "domain": detect_experience_domain(
                    matched_text
                ),
                "text": matched_text,
            })
            
            matched_spans.append(
                (start, end)
            )
    return requirements

def extract_qualifications(description):
    sections = split_job_sections(description)

    qualifications = {
        "required": [],
        "preferred": [],
    }

    for section_name in ("required", "preferred"):
        text = sections[section_name]

        # Years of experience
        experience_requirements = (
            extract_experience_requirements(text)
        )
        
        qualifications[section_name].extend(
            experience_requirements
        )
        
        # Bachelor's degree
        degree_requirements = extract_degree_requirements(
            text
        )
        
        qualifications[section_name].extend(
            degree_requirements
        )

        # Production software
        if re.search(
            r"\bproduction[-\s]+(?:quality\s+)?software\b",
            text,
            re.IGNORECASE
        ):
            qualifications[section_name].append({
                "type": "production_software",
                "value": True,
                "text": "Production software experience",
            })

        # Software best practices
        if re.search(
            r"\bsoftware\s+best\s+practices\b",
            text,
            re.IGNORECASE
        ):
            qualifications[section_name].append({
                "type": "software_best_practices",
                "value": True,
                "text": "Software best practices",
            })

    return qualifications

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

def calculate_skill_credit(
    required_skill,
    candidate_skills,
):
    required_skill = normalize_skill(required_skill)
    
    normalized_candidate_skills = set()
    
    for skill in candidate_skills:
        normalized_skill = normalize_skill(skill)
        
        if normalized_skill:
            normalized_candidate_skills.add(normalized_skill)
            
    if required_skill in normalized_candidate_skills:
        return 1.0

    related_skills = RELATED_SKILLS.get(
        required_skill,
        {},
    )
    
    related_credit = 0.0
    
    for candidate_skill in candidate_skills:
        credit = related_skills.get(
            candidate_skill,
            0.0,
        )
        
        related_credit = max(
            related_credit,
            credit,
        )
        
    return related_credit

def calculate_degree_field_credit(
    candidate_field,
    required_fields,
    related_field_allowed=False,
):
    if not required_fields:
        return 1.0

    if not candidate_field:
        return 0.0

    candidate_field = normalize_degree_field(
        candidate_field
    )

    normalized_required_fields = [
        normalize_degree_field(field)
        for field in required_fields
    ]

    # Exact field match.
    if candidate_field in normalized_required_fields:
        return 1.0

    # A related field only counts when the posting
    # explicitly allows related fields.
    if not related_field_allowed:
        return 0.0

    for required_field in normalized_required_fields:
        related_fields = RELATED_DEGREE_FIELDS.get(
            required_field,
            set(),
        )

        normalized_related_fields = {
            normalize_degree_field(field)
            for field in related_fields
        }

        if candidate_field in normalized_related_fields:
            return 0.75

    return 0.0    
    

def calculate_degree_qualification_credit(
    qualification,
    profile,
):
    required_degree = qualification.get(
        "minimum",
        qualification.get("value"),
    )

    candidate_degree = profile.get(
        "education",
        {},
    ).get(
        "degree_level"
    )

    # First check the actual degree.
    if (
        required_degree is not None
        and candidate_degree is not None
    ):
        required_level = DEGREE_LEVELS.get(
            required_degree,
            0,
        )

        candidate_level = DEGREE_LEVELS.get(
            candidate_degree,
            0,
        )

        if candidate_level >= required_level:
            return 1.0

    # No sufficient degree. Check whether the
    # posting explicitly allows equivalent experience.
    if qualification.get(
        "equivalent_experience",
        False,
    ):
        software_years = profile.get(
            "experience",
            {},
        ).get(
            "software_years",
            0,
        )

        # Current policy established by our tests:
        # 4+ years satisfies a bachelor's-or-equivalent
        # requirement.
        if (
            required_degree == "bachelors"
            and software_years >= 4
        ):
            return 1.0

    return 0.0
    
def calculate_experience_qualification_credit(
    qualification,
    profile,
):
    domain = qualification.get(
        "domain",
        "software",
    )

    if domain == "embedded":
        candidate_years = profile.get(
            "experience",
            {},
        ).get(
            "embedded_years",
            0,
        )
    else:
        candidate_years = profile.get(
            "experience",
            {},
        ).get(
            "software_years",
            0,
        )

    required_years = qualification.get(
        "minimum",
        qualification.get(
            "value",
            0,
        ),
    )

    if candidate_years >= required_years:
        return 1.0

    gap = required_years - candidate_years

    if gap == 1:
        return 0.75

    if candidate_years >= 2:
        return 0.4

    return 0.0
    

def classify_experience_gap(experience_gap):
    if experience_gap is None:
        return "unknown"
    
    if experience_gap == 0:
        return "none"
    
    if experience_gap <= 1:
        return "small"
    
    if experience_gap <= 3:
        return "moderate"
    
    return "large"

def calculate_experience_gap(
    qualification_comparison,
    profile,
):
    required_qualifications = (
        qualification_comparison["required_matched"]
        + qualification_comparison["required_missing"]
    )

    experience_gaps = []

    for qualification in required_qualifications:
        if qualification["type"] != "years_experience":
            continue

        required_years = qualification.get(
            "minimum",
            qualification["value"]
        )

        domain = qualification.get(
            "domain",
            "software"
        )

        candidate_years = get_candidate_experience_years(
            profile,
            domain
        )

        if candidate_years is None:
            continue

        gap = max(
            required_years - candidate_years,
            0
        )

        experience_gaps.append(gap)

    if not experience_gaps:
        return None

    return max(experience_gaps)

def compare_qualifications(
    qualifications,
    profile,
):
    result = {
        "required_matched": [],
        "required_missing": [],
        "preferred_matched": [],
        "preferred_missing": [],
        "required_credit": 0.0,
        "preferred_credit": 0.0,
    }

    profile_experience = profile.get(
        "experience",
        {},
    )

    profile_education = profile.get(
        "education",
        {},
    )

    profile_degree = profile_education.get(
        "degree_level"
    )

    profile_field = profile_education.get(
        "field"
    )

    for category in (
        "required",
        "preferred",
    ):
        matched_key = f"{category}_matched"
        missing_key = f"{category}_missing"
        credit_key = f"{category}_credit"

        for qualification in qualifications.get(
            category,
            [],
        ):
            qualification_type = qualification.get(
                "type"
            )

            credit = 0.0
            
            if qualification_type == "years_experience":
                credit = (
                    calculate_experience_qualification_credit(
                        qualification,
                        profile,
                    )
                )

            elif qualification_type == "degree":
                degree_credit = (
                    calculate_degree_qualification_credit(
                        qualification,
                        profile,
                    )
                )

                if degree_credit > 0.0:
                    required_fields = qualification.get(
                        "fields",
                        [],
                    )

                    # If the candidate has no degree but qualifies
                    # through equivalent experience, there is no
                    # degree field to compare.
                    equivalent_experience_used = (
                        profile_degree is None
                        and qualification.get(
                            "equivalent_experience",
                            False,
                        )
                    )

                    if (
                        not required_fields
                        or equivalent_experience_used
                    ):
                        field_credit = 1.0
                    else:
                        field_credit = (
                            calculate_degree_field_credit(
                                profile_field,
                                required_fields,
                                qualification.get(
                                    "related_field_allowed",
                                    False,
                                ),
                            )
                        )

                    credit = min(
                        degree_credit,
                        field_credit,
                    )

            elif qualification_type == "production_software":
                credit = (
                    1.0
                    if profile_experience.get(
                        "production_software",
                        False,
                    )
                    else 0.0
                )

            elif qualification_type == "software_best_practices":
                credit = (
                    1.0
                    if profile_experience.get(
                        "software_best_practices",
                        False,
                    )
                    else 0.0
                )

            else:
                # Preserve the existing behavior for
                # qualification types that do not require
                # specialized scoring.
                credit = 0.0

            result[credit_key] += credit

            if credit > 0:
                result[matched_key].append(
                    qualification
                )
            else:
                result[missing_key].append(
                    qualification
                )

    return result

def compare_profile(job_skills, profile):
    candidate_skills = set ()
    
    for skill in profile["skills"]:
        normalized_skill = normalize_skill(skill)
        
        if normalized_skill:
            candidate_skills.add(normalized_skill)
    
    results = {
        "required_matched": [],
        "required_missing": [],
        "preferred_matched": [],
        "preferred_missing": [],
        "general_matched": [],
        "general_missing": [],
        "skill_credits": {},
    }
    
    for item in job_skills:
        skill = item["skill"]
        section = item["section"]

        credit = calculate_skill_credit(skill, candidate_skills,)
        
        results["skill_credits"][skill] = credit
        
        if section == "required":
            if credit > 0.0:
                results["required_matched"].append(skill)
            else:
                results["required_missing"].append(skill)
        elif section == "preferred":
            if credit > 0.0:
                results["preferred_matched"].append(skill)
            else:
                results["preferred_missing"].append(skill)
        else:
            if credit > 0.0:
                results["general_matched"].append(skill)
            else:
                results["general_missing"].append(skill)
                
    return results
            


def calculate_qualification_match(
    matched,
    missing,
    profile=None,
):
    qualifications = matched + missing
    
    if not qualifications:
        return None
    
    total_credit = 0.0
    
    for qualification in qualifications:
        qualification_type = qualification["type"]
        
        if qualification_type == "years_experience":
            if profile is None:
                credit = (
                    1.0
                    if qualification in matched
                    else 0.0
                )
            else:
                credit = calculate_experience_qualification_credit(
                    qualification,
                    profile,
                )
        else:
            credit = (
                1.0
                if qualification in matched
                else 0.0
            )
        total_credit += credit
        
    return (
        total_credit
        / len(qualifications)
        * 100
    )
    
    

def calculate_weighted_match(
    matched,
    missing,
    track,
    skill_credits=None,
):
    if skill_credits is None:
        skill_credits = {}
        
    all_skills = matched + missing
    
    if not all_skills:
        return None
    
    earned_weight = 0.0
    total_weight = 0.0
    
    for skill in all_skills:
        weight = get_skill_weight(skill, track,)
        
        total_weight += weight
        
        if skill in skill_credits:
            credit = skill_credits[skill]
        elif skill in matched:
            # Preserve the old behavior for callers that
            # do noy provide skill_credits.
            credit = 1.0
        else:
            credit = 0.0
            
        earned_weight += weight * credit
    
    if total_weight == 0:
        return None

    return (
        earned_weight /total_weight * 100
    )
            
def calculate_skill_percentages(
    comparison,
    track,
):
  
    skill_credits = comparison.get(
        "skill_credits",
        {},
    )
    
    return {
        "required": calculate_weighted_match(
            comparison["required_matched"],
            comparison["required_missing"],
            track,
            skill_credits,
        ),
        "preferred": calculate_weighted_match(
            comparison["preferred_matched"],
            comparison["preferred_missing"],
            track,
            skill_credits,
        ),
        "general": calculate_weighted_match(
            comparison["general_matched"],
            comparison["general_missing"],
            track,
            skill_credits,
        ),
    }


def calculate_fit_score(comparison, track):
    percentages = calculate_skill_percentages(
        comparison,
        track,
    )
    
    required_percentage = percentages["required"]
    preferred_percentage = percentages["preferred"]
    general_percentage = percentages["general"]
    
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

def calculate_overall_fit(
    skill_fit,
    required_qualification_percentage,
    preferred_qualification_percentage
):
    weighted_total = skill_fit * 0.70
    total_weight = 0.70
    
    if required_qualification_percentage is not None:
        weighted_total += (
            required_qualification_percentage / 10
        ) * 0.25
        total_weight += 0.25
        
    if preferred_qualification_percentage is not None:
        weighted_total += (
            preferred_qualification_percentage / 10
        ) * 0.05
        total_weight += 0.05
        
    if total_weight == 0:
        return 0.0
    
    return round(weighted_total / total_weight, 1)

        
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
    
    # Compound headings used by Workday and other ATS sites.
    required_phrases = [
        "required qualifications",
        "minimum qualifications",
        "basic qualifications",
    ]
    
    preferred_phrases = [
        "preferred qualifications",
        "desired qualifications",
        "nice to have",
        "nice-to-have",
    ]
    
    if any(phrase in heading for phrase in required_phrases):
        return "required"
    
    if any(phrase in heading for phrase in preferred_phrases):
        return "preferred"

    return None


def find_skill_section(skill, sections):
    if skill_matches(skill, sections["required"]):
        return "required"    
    
    if skill_matches(skill, sections["preferred"]):
        return "preferred"
    
    if skill_matches(skill, sections["general"]):
        return "general"

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

def allows_related_degree_field(text):
    return bool(
        re.search(
            r"\b(?:related|relevant|similar|"
            r"closely related|equivalent)\s+field\b",
            text,
            re.IGNORECASE,
        )
    )

def extract_degree_fields(text):
    text_lower = text.lower()

    field_patterns = {
        "computer science": [
            r"\bcomputer science\b",
        ],
        "computer engineering": [
            r"\bcomputer engineering\b",
        ],
        "electrical engineering": [
            r"\belectrical engineering\b",
        ],
        "software engineering": [
            r"\bsoftware engineering\b",
        ],
    }

    fields = []

    for field, patterns in field_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                fields.append(field)
                break

    return fields

def normalize_skill(skill):
    if not skill:
        return None
    
    normalized = " ".join(
        skill.lower().strip().split()
    )
    
    return SKILL_ALIASES.get(
        normalized,
        normalized,
    )

def normalize_degree_field(field):
    if not field:
        return None
    
    field = field.lower().strip()
    
    aliases = {
        "cs": "computer science",
        "comp sci": "computer science",
        "computer sciences": "computer science",
        
        "se": "software engineering",
        "software eng": "software engineering",
        
        "ce": "computer engineering",
        "computer systems engineering": "computer engineering",
        "comp eng": "computer engineering",
        
        "ee": "electrical engineering",
        "electrical and computer engineering": "electrical engineering",
        "electrical eng": "electrical engineering",
        
        "ece": "electrical and computer engineering",
    }
    
    return aliases.get(field, field)

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
            
            if url and row_url:
                try:
                    new_url = normalize_url(url)
                    existing_url = normalize_url(row_url)
                    
                    if new_url == existing_url:
                        return True
                    
                except ValueError:
                    pass
                
                # Both jobs have valid-looking URLs,
                # but they're different postings
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
    return False

def processed_job_exists(job, csv_filename="jobs.csv"):
    return job_exists(
        csv_filename,
        job["company"],
        job["role"],
        job["url"]
    )

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
        
        writer.writerow({
            "Company": company,
            "Role": role,
            "URL": url,
            "Location": location,
            "Job Track": track,
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
        
def save_processed_job(job, csv_filename="jobs.csv"):
    save_job(
        csv_filename,
        job["company"],
        job["role"],
        job["url"],
        job["location"],
        job["track"],
        job["track_score"],
        job["fit_score"],
        job["required_percentage"],
        job["preferred_percentage"],
        job["recommendation"],
        job["priority"],
        job["required_missing"],
        job["resume"],
        job["description_file"],
    )
    
    print()
    print("Job added to jobs.csv")
        
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
    
    skill_credits = comparison.get(
        "skill_credits",
        {},
    )
    
    skill_percentages = calculate_skill_percentages(
        comparison,
        resume,
    )
    
    required_percentage = skill_percentages["required"]
    preferred_percentage = skill_percentages["preferred"]
    general_percentage = skill_percentages["general"]
    
    qualifications = extract_qualifications(description)

    qualification_comparison = compare_qualifications(
        qualifications,
        profile
    )
    
    experience_gap = calculate_experience_gap(
        qualification_comparison,
        profile,
    )
    
    experience_gap_severity = classify_experience_gap(experience_gap)
    
    critical_missing_qualifications = (
        count_critical_missing_qualifications(
            qualification_comparison,
            experience_gap_severity,
        )
    )

    
    required_qualification_percentage = (
        calculate_qualification_match(
            qualification_comparison["required_matched"],
            qualification_comparison["required_missing"],
            profile,
        )
    )
    
    preferred_qualification_percentage = (
        calculate_qualification_match(
            qualification_comparison["preferred_matched"],
            qualification_comparison["preferred_missing"],
            profile,
        )
    )

    skill_fit_score = calculate_fit_score(comparison, resume)
    
    fit_score = calculate_overall_fit(
        skill_fit_score,
        required_qualification_percentage,
        preferred_qualification_percentage,
    )
    

    missing_core_skills = count_missing_core_skills(comparison, resume)
    
    recommendation = recommend_application(
        fit_score,
        required_percentage,
        missing_core_skills,
        required_qualification_percentage,
        critical_missing_qualifications,
        experience_gap_severity,
    )
    
    priority = calculate_priority(
        recommendation,
        fit_score,
        required_percentage,
        experience_gap_severity,
    )
    
    return {
        "company": company,
        "role": role,
        "url": url,
        "location": location,
        
        "track": resume,
        "track_score": track_score,
        "resume": resume,
        
        "skill_fit_score": skill_fit_score,
        "fit_score": fit_score,
        
        "required_percentage": required_percentage,
        "preferred_percentage": preferred_percentage,
        "general_percentage": general_percentage,
        
        "required_matched": comparison["required_matched"],
        "required_missing": comparison["required_missing"],
        
        "preferred_matched": comparison["preferred_matched"],
        "preferred_missing": comparison["preferred_missing"],
        
        "required_qualification_percentage":
            required_qualification_percentage,
            
        "preferred_qualification_percentage":
            preferred_qualification_percentage,

        "required_qualifications_matched":
            qualification_comparison["required_matched"],

        "required_qualifications_missing":
            qualification_comparison["required_missing"],

        "preferred_qualifications_matched":
            qualification_comparison["preferred_matched"],

        "preferred_qualifications_missing":
            qualification_comparison["preferred_missing"],
        "critical_missing_qualifications": critical_missing_qualifications,
        "experience_gap": experience_gap,
        "experience_gap_severity": experience_gap_severity,
        "missing_core_skills": missing_core_skills,
        "recommendation": recommendation,
        "priority": priority,
        
        "description_file": str(filename),
    }
    

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python score_job.py "
            "<job_description_file>"
        )
        sys.exit(1)

    filename = sys.argv[1]

    try:
        job = process_job(filename)
    except FileNotFoundError:
        print(f"Error: File not found: {filename}")
        sys.exit(1)
    except ValueError as error:
        print(f"Error: {error}")
        sys.exit(1)

    company = job["company"]
    role = job["role"]
    url = job["url"]
    location = job["location"]

    resume = job["resume"]
    track_score = job["track_score"]
    fit_score = job["fit_score"]

    required_percentage = job["required_percentage"]
    preferred_percentage = job["preferred_percentage"]
    general_percentage = job["general_percentage"]

    required_matched = job["required_matched"]
    required_missing = job["required_missing"]

    preferred_matched = job["preferred_matched"]
    preferred_missing = job["preferred_missing"]

    recommendation = job["recommendation"]
    priority = job["priority"]

    # --------------------------------------------------
    # Job information
    # --------------------------------------------------

    print("\n" + "=" * 50)
    print("JOB")
    print("=" * 50)

    print(f"Company:   {company}")
    print(f"Role:      {role}")

    if location:
        print(f"Location:  {location}")

    if url:
        print(f"URL:       {url}")

    # --------------------------------------------------
    # Classification
    # --------------------------------------------------

    print("\n" + "=" * 50)
    print("JOB CLASSIFICATION")
    print("=" * 50)

    print(f"Recommended resume: {resume}")
    print(f"Track score:        {track_score}/10")

    # --------------------------------------------------
    # Candidate fit
    # --------------------------------------------------

    print("\n" + "=" * 50)
    print("CANDIDATE FIT")
    print("=" * 50)

    if required_percentage is not None:
        print(
            f"Required match:  "
            f"{required_percentage:.0f}%"
        )
    else:
        print("Required match:  N/A")

    if preferred_percentage is not None:
        print(
            f"Preferred match: "
            f"{preferred_percentage:.0f}%"
        )
    else:
        print("Preferred match: N/A")

    if general_percentage is not None:
        print(
            f"General match:   "
            f"{general_percentage:.0f}%"
        )
    else:
        print("General match:   N/A")

    print(f"Overall fit:     {fit_score}/10")

    # --------------------------------------------------
    # Required skills
    # --------------------------------------------------

    print("\nRequired skills matched:")

    if required_matched:
        for skill in required_matched:
            weight = get_skill_weight(skill, resume)
            print(f"  ✓ {skill} (weight: {weight})")
    else:
        print("  None")

    print("\nRequired skills missing:")

    if required_missing:
        for skill in required_missing:
            weight = get_skill_weight(skill, resume)
            print(f"  ✗ {skill} (weight: {weight})")
    else:
        print("  None")

    # --------------------------------------------------
    # Preferred skills
    # --------------------------------------------------

    print("\nPreferred skills matched:")

    if preferred_matched:
        for skill in preferred_matched:
            print(f"  ✓ {skill}")
    else:
        print("  None")

    print("\nPreferred skills missing:")

    if preferred_missing:
        for skill in preferred_missing:
            print(f"  ✗ {skill}")
    else:
        print("  None")

    # --------------------------------------------------
    # Recommendation
    # --------------------------------------------------

    print("\n" + "=" * 50)
    print("APPLICATION RECOMMENDATION")
    print("=" * 50)

    print(f"Recommendation: {recommendation}")
    print(f"Priority:       {priority}")
    print(f"Resume:         {resume}")
    print(f"Overall fit:    {fit_score}/10")

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

    # --------------------------------------------------
    # CSV
    # --------------------------------------------------

    csv_filename = "jobs.csv"

    if job_exists(
        csv_filename,
        company,
        role,
        url
    ):
        print("\nJob already exists in jobs.csv")
    else:
        save_processed_job(job)