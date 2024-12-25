import logging
from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Enable logging
logging.basicConfig(level=logging.DEBUG)

# Configuration for websites
SCRAPER_CONFIG = {
    "vox": {
        "url": "https://kwt.voxcinemas.com/movies/whatson",
        "selectors": {
            "movie_block": "article.movie-summary.ghost.reveal",
            "title": "h3",
            "language": "p.language",
            "image_url": "img.lazy.poster.loaded",
        },
    },
    # Add more site configurations here if needed
}

def unified_scraper(site_code):
    try:
        if site_code not in SCRAPER_CONFIG:
            return {"error": f"Invalid site_code: {site_code}"}

        config = SCRAPER_CONFIG[site_code]
        url = config["url"]
        selectors = config["selectors"]

        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logging.error(f"Failed to retrieve data from {site_code}: {response.status_code}")
            return {"error": f"Failed to retrieve data from {site_code}"}

        soup = BeautifulSoup(response.content, "html.parser")
        movies = []

        for movie_block in soup.select(selectors["movie_block"]):
            title = movie_block.select_one(selectors.get("title"))
            language = movie_block.select_one(selectors.get("language"))
            image_url = movie_block.select_one(selectors.get("image_url"))

            movies.append({
                "title": title.text.strip() if title else "Unknown",
                "language": language.text.strip() if language else "Unknown",
                "image_url": image_url["src"] if image_url else None,
            })

        logging.debug(f"Scraped {len(movies)} movies from {site_code}")
        return movies

    except Exception as e:
        logging.exception(f"Error scraping {site_code}: {str(e)}")
        return {"error": str(e)}

# Test route for debugging
@app.route("/scrape-movies", methods=["GET"])
def scrape_movies():
    site_code = request.args.get("site_code", "vox")
    if not site_code:
        return jsonify({"error": "site_code parameter is required"}), 400

    result = unified_scraper(site_code)
    return jsonify({site_code: result})


if __name__ == "__main__":
    app.run(debug=True)
