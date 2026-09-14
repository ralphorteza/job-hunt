#!/usr/bin/env python3
import sys

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

if __name__ == "__main__":
    '''    description = """
    We are looking for an embedded firmware engineer experienced with stm32, c++, spi, i2c, linux, and real-time systems.
    """
    '''
    if len(sys.argv) != 2:
        print("Usage: python score_job.py <job_description_file>")
        sys.exit(1)
    
    filename = sys.argv[1]

    with open(filename, "r", encoding="utf-8") as file:
        description = file.read()

    raw_score, matches = score_job(description)
    normalize_score = normalize(raw_score)
    resume = choose_resume(description)

    print(f"Raw score: {raw_score}")
    print(f"Match score: {normalize_score}/10")
    print(f"Skills matched: {matches}")
    print(f"Reccomended resume: {resume}")

