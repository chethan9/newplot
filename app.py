from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Endpoint to scrape movie data
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

        # Extract movie details (adjust selectors based on website's structure)
        movies = []
        for movie in soup.select('.movie-card'):  # Adjust '.movie-card' as needed
            title = movie.select_one('.movie-title').text.strip() if movie.select_one('.movie-title') else "Unknown"
            genre = movie.select_one('.movie-genre').text.strip() if movie.select_one('.movie-genre') else "Unknown"
            movies.append({"title": title, "genre": genre})

        return jsonify({"movies": movies}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
