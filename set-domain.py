#!/usr/bin/env python3
"""Replace the starter domain in Arcadia Global 100 static-site files."""
from pathlib import Path
from urllib.parse import urlparse
import sys

ROOT = Path(__file__).resolve().parent
OLD = "https://YOUR-DOMAIN.example"
TEXT_SUFFIXES = {".html", ".xml", ".txt", ".json", ".webmanifest", ".md", ".js", ".css"}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python set-domain.py https://your-real-domain.com")
        return 2
    domain = sys.argv[1].strip().rstrip("/")
    parsed = urlparse(domain)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
        print("Enter the root domain with HTTPS, e.g. https://example.com")
        return 2
    changed = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES or path.name == Path(__file__).name:
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = original.replace(OLD, domain)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"Updated the site domain in {changed} text files to {domain}")
    print("Next: add your Search Console verification token and support email, then deploy and submit /sitemap.xml.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
