from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

# OMDb API Key
OMDB_API_KEY = "ae3bdd47"

# Updated Configuration for VOX Website
SCRAPER_CONFIG = {
    "vox": {
        "url": "https://kwt.voxcinemas.com/movies/whatson",
        "selectors": {
            "movie_block": "article.movie-summary.ghost.reveal",
            "title": "h3",
            "language": "p.language",
            "image_url": "img.lazy.poster.loaded",
        },
    }
}

# Selenium scraper for dynamic content
def selenium_scraper(url, selectors):
    options = Options()
    options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, selectors["movie_block"]))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        movies = []
        for movie_block in soup.select(selectors["movie_block"]):
            title = (
                movie_block.select_one(selectors["title"]).text.strip()
                if movie_block.select_one(selectors["title"])
                else "Unknown"
            )
            language = (
                movie_block.select_one(selectors["language"]).text.strip()
                if movie_block.select_one(selectors["language"])
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
                    "language": language,
                    "image_url": image_url,
                }
            )
        return movies
    finally:
        driver.quit()

# API endpoint for scraping
@app.route("/scrape-vox", methods=["GET"])
def scrape_vox():
    config = SCRAPER_CONFIG["vox"]
    try:
        movies = selenium_scraper(config["url"], config["selectors"])
        return jsonify({"vox": movies})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
