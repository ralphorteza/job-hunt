import sys
from pathlib import Path

from score_job import (
    process_job,
    job_exists,
    save_job,
)

PRIORITY_ORDER = {
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 2,
}

def sort_jobs(jobs):
    return sorted(
        jobs,
        key=lambda job: (
            PRIORITY_ORDER.get(job["priority"],99),
            -job["fit_score"],
            -(
                job["required_percentage"]
                if job["required_percentage"] is not None
                else 0
            ),
        )
    )
    
def print_queue(jobs):
    if not jobs:
        print("\nNo new jobs added.")
        return
    
    jobs = sort_jobs(jobs)
    
    print("\n")
    print("=" * 80)
    print("APPLICATION QUEUE")
    print("=" * 80)
    
    for index, job in enumerate(jobs, start=1):
        required = job["required_percentage"]
        
        if required is None:
            required_text = "N/A"
        else:
            required_text = f"{required:.0f}%"
        
        print(
            f"{index:>2}. "
            f"[{job['priority']:<6}] "
            f"{job['company']} - "
            f"{job['role']}"
        )
        
        print(
            f"  Fit: {job['fit_score']}/10"
            f"  |  Required: {required_text}"
            f"  |  {job['recommendation']}"
            f"  |  Resume: {job['resume']}"
        )

def find_job_files(directory):
    directory = Path(directory)
    
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")
    
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    
    return sorted(directory.glob("*.txt"))

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
    
def process_directory(directory, csv_filename="jobs.csv"):
    files = find_job_files(directory)
    
    processed_jobs = []
    skipped_duplicates = 0
    failed_jobs = []
    
    for filename in files:
        print(f"Processing: {filename.name}")
        
        try:
            job = process_job(filename)
            
            if job_exists(
                csv_filename,
                job["company"],
                job["role"],
                job["url"],
            ):
                print("   Duplicate - skipped")
                skipped_duplicates += 1
                continue
            
            save_processed_job(job, csv_filename)
            processed_jobs.append(job)
            
            print(
                f"   {job['recommendation']} "
                f"|  {job['priority']} "
                f"| Fit {job['fit_score']}/10"
            )
        except (ValueError, OSError) as error:
            print(f"   Error: {error}")
            failed_jobs.append({
                "file": str(filename),
                "error": str(error),
            })
            
    return (processed_jobs, skipped_duplicates, failed_jobs)


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python scripts/score_jobs.py"
            "<description_directory>"            
        )
        sys.exit(1)
        
    directory = sys.argv[1]
    
    try:
        jobs, duplicates, failures = process_directory(directory)
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}")
        sys.exit(1)
        
    print_queue(jobs)
    
    print("\nBatch summary:")
    print(f"    Added:          {len(jobs)}")
    print(f"    Duplicates:     {duplicates}")
    print(f"    Failed:         {len(failures)}")
    
if __name__ == "__main__":
    main()