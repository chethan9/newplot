from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Endpoint to scrape "Showing Now" movies
@app.route('/scrape-movies', methods=['GET'])
def scrape_movies():
    try:
        # URL of the target website
        url = 'https://ozonecinemas-kw.com/'
        headers = {'User-Agent': 'Mozilla/5.0'}

        # Fetch the website content
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return jsonify({"error": "Failed to retrieve website data"}), 500

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Locate the "Showing Now" section
        showing_now_section = soup.select_one('#pills-sn-tab')  # Replace with the correct ID or class for "Showing Now"
        if not showing_now_section:
            return jsonify({"error": "Showing Now section not found"}), 404

        # Extract movie details only from the "Showing Now" section
        movies = []
        for movie_block in showing_now_section.find_next_sibling('div').select('div.mv-block'):
            title = movie_block.select_one('div.mv-name').text.strip() if movie_block.select_one('div.mv-name') else "Unknown"
            genre = movie_block.select_one('div.mv-category').text.strip() if movie_block.select_one('div.mv-category') else "Unknown"
            image_url = movie_block.select_one('img.img-fluid')['src'] if movie_block.select_one('img.img-fluid') else None

            movies.append({
                "title": title,
                "genre": genre,
                "image_url": image_url
            })

        return jsonify({"movies": movies}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
