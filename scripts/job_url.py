import json
import re

import requests
from bs4 import BeautifulSoup
from copy import deepcopy
from urllib.parse import (
    urlparse,
    urlunparse,
    parse_qsl,urlencode
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "Chrome/120 Safari/537.36"
    )
}

TRACKING_PARAMS = {
    "source",
    "src",
    "ref",
    "referrer",
    "tracking",
    "trackingid",
    "gh_src",
}

def normalize_url(url):
    parsed = urlparse(url)
    query_params = parse_qsl(parsed.query, keep_blank_values=True)
    filtered_params = []
    
    for key, value in query_params:
        key_lower = key.lower()
        
        if key_lower.startswith("utm_"):
            continue
        
        if key_lower in TRACKING_PARAMS:
            continue
        
        filtered_params.append( (key, value) )
    
    query = urlencode(filtered_params, doseq=True)
    
    path = parsed.path
    if path != "/":
        path = path.rstrip("/")
    
    normalized = parsed._replace(
        scheme=parse.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=path,
        query=query,
        fragment=""
    )
    
    return urlunparse(normalized)
    
    

def validate_url(url):
    url = url.strip()
    
    if not url:
        raise ValueError("URL cannot be empty.")
    
    parsed = urlparse(url)
        
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must begin with http:// or https://")
    
    if not parsed.netloc:
        raise ValueError("URL is missing a hostname.")
    
    return url
    


def extract_html_fallback(soup, url):
    company = extract_description_from_html(soup)
    
    role = extract_description_from_html(soup)
    role = clean_job_title(role)

    location = extract_description_from_html(soup)
    description = extract_description_from_html(soup)
    
    if not description:
        raise ValueError("Could not extract a usable job desctription from HTML")
    
    return {
        "company": company,
        "role": role,
        "url": url,
        "location": location,
        "description": description,
        "extraction_method": "html",
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
    url = validate_url(url)
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=15,
        allow_redirects=True
    )
    
    response.raise_for_status()
    final_url = response.url
    
    return response.text, final_url

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

def is_valid_description(text):
    if not text:
        return False
    
    # Job descriptions should normally containt
    # subtantially more than a page title.
    if len(text) < 200:
        return False
    
    words = text.split()
    
    if len(words) < 30:
        return False
    
    return True

def clean_description(text):
    if not text:
        return ""
    
    lines = []
    
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        
        if line:
            lines.append(line)
            
    return "\n".join(lines)

def extract_description_from_html(soup):
    selectors = [
        "[data-job-description]",
        ".job-description",
        "#job-description",
        ".jobDescription",
        "article",
        "main",
    ]
    
    for selector in selectors:
        element = soup.select_one(selector)
        
        if not element:
            continue
        
        element = deepcopy(element)
        remove_page_noise(element)
        
        text = element.get_text("separator=\n",strip=True)
        text = clean_description(text)
        
        if is_valid_description(text):
            return text
        
    return ""

def remove_page_noise(soup):
    for element in soup.select(
        "script, style, nav, footer, "
        "header, noscript, iframe"
    ):
        element.decompose()
        
    return soup

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

def extract_location_from_html(soup):
    selectors = [
        "[data-job-location]",
        ".job-location",
        ".location",
        ".jobLocation",
        ".job-location-name",
    ]
    
    for selector in selectors:
        element = soup.select_one(selector)
        
        if element:
            text = clean_text(element.get_text(" ", strip=True))
            if text:
                return text
    
    return ""

def extract_job_from_html(soup):
    company = get_meta_content(soup, "og:site_name")
    
    if company:
        return company
    
    selectors = [
        "[data-company-name]",
        ".company-name",
        ".employer-name",
        ".hiring-organization",
    ]
    
    for selector in selectors:
        element = soup.select_one(selector)
        
        if element:
            text = clean_text(element.get_text(" ", strip=True))
            if text:
                return text
    
    return ""

def extract_job_from_url(url):
    original_url = validate_url(url)
    html, final_url = fetch_page(original_url)
    normalized_url = normalize_url(final_url)
    soup = BeautifulSoup(html, "html.parser")
    posting = extract_json_ld(soup)
    
    # Preferred method
    if posting:
        company = extract_company(posting)
        role = clean_text( str(posting.get("title", "")))
        location = extract_location(posting)
        
        description_html = str(posting.get("description", ""))
        description = clean_html(description_html)
        if description:
            return {
                "company": company,
                "role": role,
                "url": url,
                "location": location,
                "description": description,
                "extraction_method": "json-ld",
            }
            
    # Fall back to the regular HTML.
    job = extract_html_fallback(soup, normalized_url)
    
    job["original_url"] = original_url
    job["final_url"] = final_url
    
    
    
    

'''
BELOW IS TESTING THE MAIN SCRIPT! COMMENT OUT IF NOT IN USE!
'''
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python scripts/job_url.py <URL>")
        sys.exit(1)
    try:    
        job = extract_job_from_url(sys.argv[1])
    except (ValueError, requests.RequestException) as error:
        print(f"Error: {error}")
        sys.exit(1)
        
    print(f"Extraction: {job['extraction_method']}")
    print(f"Company: {job['company']}")
    print(f"Role: {job['role']}")
    print(f"Location: {job['location']}")
    
    print("\nDescription: \n")
    print(job["description"])
    
    