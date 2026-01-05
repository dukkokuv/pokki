#!/usr/bin/env python3
"""
scrape_voot.py
Scrape the given PRMovies page and write voot.json with structure you requested.
Requirements: requests, beautifulsoup4
Install: pip install requests beautifulsoup4
"""

from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import json
import re
import time

# CONFIG
URL = "https://watchofree.beer/director/netflix/"
OUTPUT_FILE = "voot.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})

def safe_text(el) -> Optional[str]:
    if not el: 
        return None
    txt = el.get_text(separator=" ", strip=True)
    return txt if txt != "" else None

def parse_duration(text: str) -> Optional[str]:
    if not text:
        return None
    # common form "77 min" etc.
    return text.strip()

def parse_imdb(text: str) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"(\d+(\.\d+)?)", text)
    if m:
        try:
            return float(m.group(1))
        except:
            return None
    return None

def extract_movies_from_soup(soup: BeautifulSoup) -> List[Dict]:
    movies = []
    container = soup.find("div", class_="movies-list")
    if not container:
        return movies

    items = container.find_all("div", class_="ml-item")
    for it in items:
        try:
            # id
            data_id = it.get("data-movie-id") or it.get("data-id") or ""
            try:
                mid = int(data_id) if data_id else None
            except:
                mid = None

            a = it.find("a", class_="ml-mask")
            title = None
            if a:
                h2 = a.find("h2")
                if h2:
                    title = safe_text(h2)
                # link/watch
                watch_link = a.get("href") or None
                # language/quality
                lang_el = a.find("span", class_="mli-quality")
                language = safe_text(lang_el)
                # thumbnail
                img = a.find("img")
                thumbnail = None
                if img:
                    thumbnail = img.get("data-original") or img.get("src") or None

            # hidden_tip block for details
            hidden = it.find(id="hidden_tip")
            # fallback: some pages might include a separate jtip or qtip
            if not hidden:
                hidden = it

            # description
            desc_el = hidden.find("p", class_="f-desc")
            description = None
            if desc_el:
                # sometimes nested <p> inside
                inner_p = desc_el.find("p")
                if inner_p:
                    description = safe_text(inner_p)
                else:
                    description = safe_text(desc_el)

            # year and year link
            year = None
            year_link = None
            year_tag = hidden.find("a", href=re.compile(r"/release-year/"))
            if year_tag:
                ytxt = safe_text(year_tag)
                try:
                    year = int(re.search(r"\d{4}", ytxt).group(0))
                except:
                    year = None
                year_link = year_tag.get("href")

            # imdb
            imdb_el = hidden.find("div", class_=re.compile(r"jt-imdb"))
            imdb_rating = None
            if imdb_el:
                imdb_rating = parse_imdb(safe_text(imdb_el))

            # duration (one of jt-info divs)
            duration = None
            jt_infos = hidden.find_all("div", class_="jt-info")
            for ji in jt_infos:
                txt = safe_text(ji)
                if txt and re.search(r"\d+\s*min", txt, re.I):
                    duration = parse_duration(txt)
                    break
            # country
            country = None
            country_link = None
            block_country = hidden.find("div", string=re.compile(r"Country:", re.I))
            if block_country:
                # find link inside
                a_country = block_country.find("a")
                if a_country:
                    country = safe_text(a_country)
                    country_link = a_country.get("href")

            # genres
            genres = []
            genre_links = []
            # look for div with "Genre:" text
            genre_div = hidden.find("div", string=re.compile(r"Genre:", re.I))
            if genre_div:
                for a_gen in genre_div.find_all("a"):
                    g = safe_text(a_gen)
                    if g:
                        genres.append(g)
                        genre_links.append(a_gen.get("href"))
            else:
                # fallback: find all genre links under this item
                for a_gen in hidden.find_all("a", href=re.compile(r"/genre/")):
                    g = safe_text(a_gen)
                    if g and g not in genres:
                        genres.append(g)
                        genre_links.append(a_gen.get("href"))

            movie = {
                "id": mid,
                "title": title,
                "year": year,
                "language": language,
                "imdb_rating": imdb_rating,
                "duration": duration,
                "thumbnail": thumbnail,
                "description": description,
                "country": country,
                "genres": genres,
                "links": {
                    "watch": watch_link,
                    "year": year_link,
                    "country": country_link,
                    "genres": genre_links
                }
            }

            movies.append(movie)
        except Exception as e:
            # continue on errors per item
            print("Error parsing item:", e)
            continue

    return movies

def fetch_html(url: str, tries: int = 3, backoff: float = 1.0) -> Optional[str]:
    for attempt in range(tries):
        try:
            r = session.get(url, timeout=20)
            if r.status_code == 200:
                return r.text
            else:
                print(f"Fetch attempt {attempt+1} returned status {r.status_code}")
        except Exception as e:
            print(f"Fetch attempt {attempt+1} error: {e}")
        time.sleep(backoff * (attempt+1))
    return None

def main():
    html = fetch_html(URL)
    if not html:
        print("Failed to fetch HTML from", URL)
        return

    soup = BeautifulSoup(html, "lxml")
    movies = extract_movies_from_soup(soup)

    out = {"movies": movies}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(movies)} movies to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
