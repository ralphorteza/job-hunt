import re
from pathlib import Path

from score_job import(
    process_job,
    processed_job_exists,
    save_processed_job,
)

def make_filename(company, role):
    name = f"{company}_{role}".lower()
    
    # Replace non-alphanumeric characters with underscores.
    name = re.sub(r"[^a-z0-9]+", "_", name)
    
    # Remove leading/trailing underscores.
    name = name.strip("_")
    
    return f"{name}.txt"

def reading_description():
    print()
    print("Paste the job description below.")
    print("When finished. enter END on its own line.")
    print()
    
    lines = []
    
    while True:
        try:
            line = input()
        except EOFError:
            break
        
        if line.strip() == "END":
            break
        
        lines.append(line)
        
    return "\n".join(lines).strip()

def save_description(
    output_directory,
    company,
    role,
    url,
    location,
    description,
):
    output_directory = Path(output_directory)
    
    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )
    
    filename = make_filename(
        company,
        role
    )
    
    path = get_unique_path(
        output_directory,
        filename
    )
    
    content = (
        f"Company: {company}\n"
        f"Role: {role}\n"
        f"URL: {url}\n"
        f"Location: {location}\n"
        f"\n"
        f"Description:\n"
        f"{description}\n"
    )
    
    path.write_text(content, encoding="utf-8")
    
    return path

def get_unique_path(directory, filename):
    path = directory / filename
    
    if not path.exists():
        return path
    
    stem = path.stem
    suffix = path.suffix
    
    counter = 2
    
    while True:
        candidate = directory / (
            f"{stem}_{counter}{suffix}"
        )
        
        if not candidate.exists():
            return candidate
        
        counter += 1
        
def read_required(prompt):
    while True:
        value = input(prompt).strip()
        
        if value:
            return value
        
        print("This field is required.")
        
def main():
    print("=" * 50)
    print("ADD JOB")
    print("=" * 50)
    
    company = read_required(
        "Company: "
    )
    
    role = read_required(
        "Role: "
    )
    
    url = input(
        "URL (optional): "
    ).strip()
    
    location = input(
        "Location (optional): "
    ).strip()
    
    description = reading_description()
    
    if not description:
        print("Error: Job description is empty")
        return
    
    path = save_description(
        "descriptions",
        company,
        role,
        url,
        location,
        description,
    )
    
    print()
    print(f"Saved description: {path}")
    
    try:
        job = process_job(path)
        
    except (ValueError, OSError) as error:
        print(f"Error scoring job: {error}")
        return
        
    print()
    print("=" * 50)
    print("JOB ANALYSIS")
    print("=" * 50)

    print(f"Track:          {job['track']}")
    print(f"Track score:    {job['track_score']}/10")
    print(f"Fit score:      {job['fit_score']}/10")
    print(f"Recommendation: {job['recommendation']}")
    print(f"Priority:       {job['priority']}")
    
    required = job["required_percentage"]
    preferred = job["preferred_percentage"]
    
    if required is not None:
        print(
            f"Required match: {required:.0f}%"
        )
        
    if preferred is not None:
        print(
            f"Preferred match: {preferred:.0f}%"
        )
        
    if processed_job_exists(job):
        print()
        print("Job already exists in jobs.csv")
        return
    
    print("Job added to jobs.csv")
    
if __name__ == "__main__":
    main()