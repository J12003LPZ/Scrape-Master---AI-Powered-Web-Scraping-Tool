from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pandas as pd
import json
from scraper import fetch_html_selenium, html_to_markdown_with_readability, create_dynamic_listing_model, create_listings_container_model, format_data

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)  # Enable CORS for all routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    url = data.get('url')
    keywords = data.get('keywords')

    # Scrape the website
    scraped_content = fetch_html_selenium(url)
    markdown = html_to_markdown_with_readability(scraped_content)

    # Create dynamic model
    DynamicListingModel = create_dynamic_listing_model(keywords)
    DynamicListingsContainer = create_listings_container_model(DynamicListingModel)

    # Process the scraped content
    formatted_data = format_data(markdown, DynamicListingsContainer, DynamicListingModel)

    try:
        cleaned_data = json.loads(formatted_data)
    except json.JSONDecodeError as e:
        return jsonify({"error": "Invalid JSON returned by AI model", "message": str(e)}), 500

    df = pd.DataFrame(cleaned_data.get('listings', []), columns=keywords)

    return jsonify({
        "result": df.to_dict(orient='records'),
    })

if __name__ == '__main__':
    app.run()
