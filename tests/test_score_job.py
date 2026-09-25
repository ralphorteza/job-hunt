import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

from score_job import (
    calculate_experience_gap,
    classify_experience_gap,
    compare_qualifications,
    recommend_application,
    calculate_priority,
    process_job,
    extract_experience_requirements,
)

@pytest.fixture
def profile():
    return {
        "skills": [
            "c",
            "c++",
            "python",
            "linux",
            "embedded linux",
        ],
        "education": {
            "degree_level": "bachelors",
            "field": "computer science",
        },
        "experience": {
            "software_years": 2,
            "embedded_years": 2,
            "production_software": True,
            "software_best_practices": True,
        }
    }
    
@pytest.mark.parametrize(
    "required_years, expected_gap, expected_severity",
    [
        (2, 0, "none"),
        (3, 1, "small"),
        (5, 3, "moderate"),
        (10, 8, "large"),
    ],
)
def test_experience_gap(
    profile,
    required_years,
    expected_gap,
    expected_severity,
):
    qualifications = {
        "required": [
            {
                "text": f"{required_years}+ years of experience",
                "type": "years_experience",
                "value": required_years,
            }
        ],
        "preferred": [],
    }
    
    qualification_comparison = compare_qualifications(
        qualifications,
        profile,
    )
    
    gap = calculate_experience_gap(
        qualification_comparison,
        profile,
    )
    
    severity = classify_experience_gap(gap)
    
    assert gap == expected_gap
    assert severity == expected_severity
    
@pytest.mark.parametrize(
    (
        "experience_severity,"
        "expected_recommendation,"
        "expected_priority"
    ),
    [
        ("none", "APPLY", "HIGH"),
        ("small", "APPLY", "MEDIUM"),
        ("moderate", "REVIEW", "MEDIUM"),
        ("large", "SKIP", "LOW")
    ],
)
def test_experience_gap_affects_recommendation_and_priority(
    experience_severity,
    expected_recommendation,
    expected_priority,
):
    # Simulate an otherwise very strong job match.
    fit_score = 9.0
    required_percentage = 100.0
    required_qualification_percentage = 100.0
    missing_core_skills = 0
    critical_missing_qualifications = 0
    
    recommendation = recommend_application(
        fit_score,
        required_percentage,
        missing_core_skills,
        required_qualification_percentage,
        critical_missing_qualifications,
        experience_severity,
    )
    
    priority = calculate_priority(
        recommendation,
        fit_score,
        required_percentage,
        experience_severity,   
    )
    
    assert recommendation == expected_recommendation
    assert priority == expected_priority
    
    
def test_process_job_integration_strong_match(tmp_path):
    job_file = tmp_path / "test_job.txt"

    job_file.write_text(
        """
Company: Test Company
Role: Embedded Software Engineer
URL: https://example.com/jobs/123
Location: San Jose, CA

Description:
We are looking for an Embedded Software Engineer.

Responsibilities
Develop embedded software using C++ and Linux.
Work with embedded Linux systems.
Develop and test production-quality software.

Required Qualifications
2+ years of experience writing production-quality software.
Bachelor's degree in Computer Science or related field.
Experience with C++11 or later.
Knowledge of software best practices.

Preferred Qualifications
Experience with Python.
Experience with embedded Linux.
Experience with Git.
""".strip(),
        encoding="utf-8",
    )

    job = process_job(job_file)

    assert job["company"] == "Test Company"
    assert job["role"] == "Embedded Software Engineer"

    assert job["track"] == "embedded"

    assert job["required_percentage"] == 100.0
    assert job["required_qualification_percentage"] == 100.0

    assert job["experience_gap"] == 0
    assert job["experience_gap_severity"] == "none"

    assert job["critical_missing_qualifications"] == 0

    assert job["recommendation"] == "APPLY"
    assert job["priority"] == "HIGH"
    
    
def test_process_job_integration_moderate_experience_gap(tmp_path):
    job_file = tmp_path / "moderate_gap_job.txt"

    job_file.write_text(
        """
Company: Test Company
Role: Embedded Software Engineer
URL: https://example.com/jobs/456
Location: San Jose, CA

Description:
We are looking for an Embedded Software Engineer.

Responsibilities
Develop embedded software using C++ and Linux.
Work with embedded Linux systems.
Develop and test production-quality software.

Required Qualifications
5+ years of experience writing production-quality software.
Bachelor's degree in Computer Science or related field.
Experience with C++11 or later.
Knowledge of software best practices.

Preferred Qualifications
Experience with Python.
Experience with embedded Linux.
Experience with Git.
""".strip(),
        encoding="utf-8",
    )

    job = process_job(job_file)

    # Basic parsing/classification
    assert job["company"] == "Test Company"
    assert job["role"] == "Embedded Software Engineer"
    assert job["track"] == "embedded"

    # Technical skills are still a strong match.
    assert job["required_percentage"] == 100.0
    assert job["skill_fit_score"] >= 8.5

    # Experience requirement should be detected as missing.
    assert job["required_qualification_percentage"] < 100.0

    # Candidate has 2 years; posting requires 5.
    assert job["experience_gap"] == 3
    assert job["experience_gap_severity"] == "moderate"

    # Moderate experience gap should downgrade the application.
    assert job["recommendation"] == "REVIEW"
    assert job["priority"] == "MEDIUM"
    
    
def test_process_job_integration_large_experience_gap(tmp_path):
    job_file = tmp_path / "large_gap_job.txt"

    job_file.write_text(
        """
Company: Test Company
Role: Embedded Software Engineer
URL: https://example.com/jobs/789
Location: San Jose, CA

Description:
We are looking for an Embedded Software Engineer.

Responsibilities
Develop embedded software using C++ and Linux.
Work with embedded Linux systems.
Develop and test production-quality software.

Required Qualifications
10+ years of experience writing production-quality software.
Bachelor's degree in Computer Science or related field.
Experience with C++11 or later.
Knowledge of software best practices.

Preferred Qualifications
Experience with Python.
Experience with embedded Linux.
Experience with Git.
""".strip(),
        encoding="utf-8",
    )

    job = process_job(job_file)

    # Basic parsing/classification
    assert job["company"] == "Test Company"
    assert job["role"] == "Embedded Software Engineer"
    assert job["track"] == "embedded"

    # Technical fit should still be strong.
    assert job["required_percentage"] == 100.0
    assert job["skill_fit_score"] >= 8.5

    # Candidate has 2 years; posting requires 10.
    assert job["experience_gap"] == 8
    assert job["experience_gap_severity"] == "large"

    # Experience gap should override the strong technical match.
    assert job["recommendation"] == "SKIP"
    assert job["priority"] == "LOW"
    
    
def test_process_job_uses_embedded_experience_years(
    tmp_path,
    monkeypatch,
):
    job_file = tmp_path / "embedded_experience_job.txt"

    job_file.write_text(
        """
Company: Test Embedded Corp
Role: Embedded Software Engineer
URL: https://example.com/jobs/embedded
Location: San Jose, CA

Description:
Job Description

We are looking for an embedded software engineer to
develop production software in C++ on embedded Linux.

Required Qualifications

5+ years of experience developing embedded Linux software

Bachelor's degree

Experience with C++

Preferred Qualifications

Experience with Python
""",
        encoding="utf-8",
    )

    profile = {
        "skills": [
            "c++",
            "python",
            "linux",
            "embedded linux",
            "embedded",
        ],
        "education": {
            "degree_level": "bachelors",
            "field": "computer science",
        },
        "experience": {
            # Deliberately different.
            "software_years": 10,
            "embedded_years": 2,
            "production_software": True,
            "software_best_practices": True,
        },
    }

    monkeypatch.setattr(
        "score_job.load_profile",
        lambda filename: profile,
    )

    job = process_job(job_file)

    assert job["experience_gap"] == 3
    assert job["experience_gap_severity"] == "moderate"

    assert (
        job["required_qualification_percentage"]
        < 100
    )

    assert job["recommendation"] == "REVIEW"
    assert job["priority"] == "MEDIUM"
    
    
    
@pytest.mark.parametrize(
    (
        "text",
        "expected_minimum",
        "expected_maximum",
        "expected_domain",
    ),
    [
        (
            "3-5 years of experience developing embedded software",
            3,
            5,
            "embedded",
        ),
        (
            "3–5 years of experience developing embedded software",
            3,
            5,
            "embedded",
        ),
        (
            "3 to 5 years of experience developing embedded software",
            3,
            5,
            "embedded",
        ),
        (
            "at least 3 years of experience developing embedded software",
            3,
            None,
            "embedded",
        ),
        (
            "minimum of 3 years of experience developing embedded software",
            3,
            None,
            "embedded",
        ),
        (
            "3 or more years of experience developing embedded software",
            3,
            None,
            "embedded",
        ),
        (
            "5+ years of experience developing embedded software",
            5,
            None,
            "embedded",
        ),
        (
            "2 years of experience writing production software",
            2,
            None,
            "software",
        ),
    ],
)
def test_extract_experience_requirements(
    text,
    expected_minimum,
    expected_maximum,
    expected_domain,
):
    requirements = extract_experience_requirements(text)
    
    assert len(requirements) == 1
    requirement = requirements[0]
    
    assert requirement["value"] == expected_minimum
    assert requirement["minimum"] == expected_minimum
    assert requirement["maximum"] == expected_maximum
    
    assert requirement["domain"] == expected_domain
    
def test_experience_range_does_not_create_duplicate_requirement():
    requirements = extract_experience_requirements(
        "3-5 years of experience developing embedded software"
    )
    
    assert len(requirements) == 1
    assert requirements[0]["minimum"] == 3
    assert requirements[0]["maximum"] == 5
    
    
def test_process_job_uses_minimum_of_experience_range(
    tmp_path,
    monkeypatch,
):
    job_file = tmp_path / "experience_range_job.txt"

    job_file.write_text(
        """
Company: Range Test Corp
Role: Embedded Software Engineer
URL: https://example.com/jobs/range-test
Location: San Jose, CA

Description:
Job Description

Develop embedded software in C++ on embedded Linux.

Required Qualifications

3-5 years of experience developing embedded software

Bachelor's degree

Experience with C++

Preferred Qualifications

Experience with Python
""",
        encoding="utf-8",
    )

    profile = {
        "skills": [
            "c++",
            "python",
            "linux",
            "embedded linux",
            "embedded",
        ],
        "education": {
            "degree_level": "bachelors",
            "field": "computer science",
        },
        "experience": {
            "software_years": 2,
            "embedded_years": 2,
            "production_software": True,
            "software_best_practices": True,
        },
    }

    monkeypatch.setattr(
        "score_job.load_profile",
        lambda filename: profile,
    )

    job = process_job(job_file)

    assert job["experience_gap"] == 1
    assert job["experience_gap_severity"] == "small"
    
    experience_qualifications = [
        qualification
        for qualification
        in job["required_qualifications_matched"]
        + job["required_qualifications_missing"]
        if qualification["type"] == "years_experience"
    ]
    
    assert len(experience_qualifications) == 1
    
    experience_requirement = ( experience_qualifications[0] )
    
    assert experience_requirement["minimum"] == 3
    assert experience_requirement["maximum"] == 5
    assert experience_requirement["domain"] == "embedded"

    assert job["recommendation"] == "REVIEW"
    assert job["priority"] == "MEDIUM"