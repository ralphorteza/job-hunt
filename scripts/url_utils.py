from urllib.parse import (
    urlparse,
    urlunparse,
    parse_qsl,urlencode
)

TRACKING_PARAMS = {
    "source",
    "src",
    "ref",
    "referrer",
    "tracking",
    "trackingid",
    "gh_src",
}

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
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=path,
        query=query,
        fragment=""
    )
    
    return urlunparse(normalized)

if __name__ == "__main__":
    test_urls = [
        (
            "https://example.com/jobs/123"
        ),
        (
            "https://example.com/jobs/123/"
        ),
        (
            "https://example.com/jobs/123"
            "?source=LinkedIn"
        ),
        (
            "https://example.com/jobs/123"
            "?utm_source=linkedin"
            "&utm_campaign=jobs"
        ),
        (
            "https://example.com/jobs/123"
            "#description"
        ),
    ]
    
    for url in test_urls:
        print(normalize_url(url))