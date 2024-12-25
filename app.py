from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# OMDb API Key
OMDB_API_KEY = "ae3bdd47"

# Configuration for websites
SCRAPER_CONFIG = {
    "ozone": {
        "url": "https://ozonecinemas-kw.com/",
        "selectors": {
            "movie_block": "div.mv-block",
            "title": "div.mv-name",
            "genre": "div.mv-category",
            "image_url": "img.img-fluid",
        },
    },
    "vox": {
        "url": "https://kwt.voxcinemas.com/movies/whatson",
        "selectors": {
            "movie_block": "article.movie-summary.ghost.reveal",
            "title": "h3",
            "language": "p.language",
            "image_url": "img.lazy.poster.loaded",
        },
    },
}

# Unified scraper function
def unified_scraper(site_code):
    if site_code not in SCRAPER_CONFIG:
        return {"error": f"Invalid site_code: {site_code}"}

    config = SCRAPER_CONFIG[site_code]
    url = config["url"]
    selectors = config["selectors"]

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return {"error": f"Failed to retrieve data from {site_code}"}

    soup = BeautifulSoup(response.content, "html.parser")
    movies = []
    for movie_block in soup.select(selectors["movie_block"]):
        title = (
            movie_block.select_one(selectors.get("title")).text.strip()
            if movie_block.select_one(selectors.get("title"))
            else "Unknown"
        )
        genre_or_language = (
            movie_block.select_one(selectors.get("genre", "language")).text.strip()
            if movie_block.select_one(selectors.get("genre", "language"))
            else "Unknown"
        )
        image_url = (
            movie_block.select_one(selectors["image_url"])["src"]
            if movie_block.select_one(selectors["image_url"])
            else None
        )
        movies.append(
            {
                "title": title,
                "genre_or_language": genre_or_language,
                "image_url": image_url,
            }
        )
    return movies

# Function to clean up data using OMDb
def clean_with_omdb(movie_title):
    url = f"http://www.omdbapi.com/?t={movie_title}&apikey={OMDB_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data.get("Response") == "True":
            return {
                "title": data.get("Title"),
                "year": data.get("Year"),
                "genre": data.get("Genre"),
                "runtime": data.get("Runtime"),
                "director": data.get("Director"),
                "poster": data.get("Poster"),
            }
        else:
            return {"error": f"Movie not found on OMDb: {movie_title}"}
    return {"error": "Failed to fetch data from OMDb"}

# Route to scrape data with optional OMDb cleanup
@app.route("/scrape-movies", methods=["GET"])
def scrape_movies():
    site_codes = request.args.get("site_code")
    use_omdb = request.args.get("use_omdb", "false").lower() == "true"

    if not site_codes:
        return jsonify({"error": "site_code parameter is required"}), 400

    site_codes = site_codes.split(",")  # Support comma-separated site codes
    all_data = {}

    for site_code in site_codes:
        all_data[site_code] = unified_scraper(site_code)

    # Optionally clean up data with OMDb
    if use_omdb:
        for site, movies in all_data.items():
            for movie in movies:
                if "title" in movie:
                    cleaned_data = clean_with_omdb(movie["title"])
                    movie.update(cleaned_data)

    if not all_data:
        return jsonify({"error": "Invalid site_code(s)"}), 400

    return jsonify(all_data)


if __name__ == "__main__":
    app.run(debug=True)
