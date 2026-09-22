import json
import re

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "Chrome/120 Safari/537.36"
    )
}

def clean_job_title(title):
    if not title:
        return ""
    separators = [
        " | Careers",
        " - Careers",
        " | Jobs",
        " - Jobs",
    ]
    
    for separator in separators:
        if separator.lower() in title.lower():
            index = title.lower().find(
                separator.lower()
            )
            
            title = title[:index]
            
    return title.strip()


def extract_title_from_html(soup):
    title = get_meta_content(soup, "og:title", "twitter:title")
    
    if title:
        return title
    
    h1 = soup.find("h1")
    
    if h1:
        return clean_text(h1.get_text(" ", strip=True))
    
    if soup.title:
        return clean_text(soup.title.get_text(" ", strip=True))

    return ""

def get_meta_content(soup, *names):
    for name in names:
        tag = soup.find("meta", attrs={"property":name})
    
        if not tag:
            tag = soup.find("meta", attrs={"name": name})
            
        if tag:
            content = tag.get("content")
            
            if content:
                return clean_text(content)
    
    return ""

def clean_text(text):
    if not text:
        return ""
    
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_page(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=15
    )
    
    response.raise_for_status()
    
    return response.text

def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    
    return soup.get_text(
        separator="\n",
        strip=True
    )

def find_jobposting(data):
    if isinstance(data, dict):
        if data.get("@type") == "JobPosting":
            return data
        
        if graph:
            result = find_jobposting(graph)
            
            if result:
                return result
            
    elif isinstance(data, list):
        for item in data:
            result = find_jobposting(item)
            
            if result:
                return result
            
    return None

def extract_json_ld(soup):
    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )
    
    for script in scripts:
        if not script.string:
            continue
        
        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            continue
        
        posting = find_jobposting(data)
        
        if posting:
            return posting
        
    return None

def extract_company(posting):
    organization = posting.get(
        "hiringOrganization",
        {}
    )
    
    if isinstance(organization, dict):
        return organization.get(
            "name",
            ""
        ).strip()
        
    return

def extract_location(posting):
    location = posting.get("jobLocation")
    
    if not location:
        return ""
    
    if isinstance(location, list):
        if not location:
            return ""
        location = location[0]
        
    if not isinstance(location, dict):
        return ""
    
    address = location.get("address", {})
    
    if not isinstance(address, dict):
        return ""
    
    parts = [
        address.get("addressLocality"),
        address.get("addressRegion"),
        address.get("addressCountry"),
    ]
    
    return ", ".join(
        str(part).strip()
        for part in parts
        if part
    )

def extract_job_from_url(url):
    html = fetch_page(url)
    
    soup = BeautifulSoup(
        html,
        "html.parser"
    )
    
    posting = extract_json_ld(soup)
    
    if not posting:
        raise ValueError(
            "No JobPosting structured data found."
        )
    
    company = extract_company(posting)
    
    # role = str(posting.get("title", "")).strip()
    role = clean_job_title(extract_title_from_html(soup))
    
    location = extract_location(posting)
    
    description_html = str(posting.get("description",""))
    
    description = clean_html(description_html)
    
    return {
        "company": company,
        "role": role,
        "url": url,
        "location": location,
        "description": description,
    }
    

'''
BELOW IS TESTING THE MAIN SCRIPT! COMMENT OUT IF NOT IN USE!
'''
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python scripts/job_url.py <URL>")
        sys.exit(1)
        
    job = extract_job_from_url(sys.argv[1])
    
    print(f"Company: {job['company']}")
    print(f"Role: {job['role']}")
    print(f"Location: {job['location']}")
    
    print("\nDescription: \n")
    print(job["description"])
    