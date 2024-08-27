from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import google.generativeai as genai
import json
from Twitter_Scraper import Twitter_Scraper

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Get the API keys from environment variables
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
NEWS_API_URL = 'https://newsapi.org/v2/everything'
USER_UNAME = os.getenv('TWITTER_USERNAME')
USER_PASSWORD = os.getenv('TWITTER_PASSWORD')
MAIL = os.getenv('MAIL')

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

@app.route("/")
def home():
    return "Hello, World!"

def analyze_article(article, topic):
    prompt = f"""
    Analyze the following news article about "{topic}":
    Title: {article['title']}
    Description: {article['description']}
    Content: {article['content']}

    Provide a JSON output with the following information:
    1. is_relevant: true if the article is relevant to the topic, false otherwise
    2. location: the specific location mentioned in the article
    3. disaster_type: the type of disaster (e.g., flood, earthquake, hurricane)
    4. tags: an array of relevant tags for easy searching and filtering
    5. severity: a rating from 1 to 10, where 10 is most severe
    6. estimated_deaths: an estimate of the number of deaths, or "unknown" if not mentioned

    If the article is not relevant or doesn't contain the required information, set the respective fields to null.

    Respond with only the JSON object, no additional text.
    """
    response = model.generate_content(prompt)
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        return None

@app.route("/news/<keyword>")
def get_news(keyword):
    params = {
        'q': keyword,
        'apiKey': NEWS_API_KEY,
        'language': 'en',
        'sortBy': 'publishedAt'
    }
    
    response = requests.get(NEWS_API_URL, params=params)
    
    if response.status_code == 200:
        news_data = response.json()
        articles = news_data.get('articles', [])
        
        # Analyze and filter articles using Gemini API
        analyzed_articles = []
        count = 0
        for article in articles:
            count += 1
            analysis = analyze_article(article, keyword)
            if analysis and analysis['is_relevant']:
                article.update(analysis)
                analyzed_articles.append(article)
            if count == 1:
                break
        
        return jsonify(analyzed_articles)
    else:
        return jsonify({'error': 'Failed to fetch news'}), 400
    
@app.route("/gemini")
def sample_prompt():
    prompt = "Who is the Prime Minister of India?"
    response = model.generate_content(prompt)
    try:
        # Assuming the Gemini API returns a response with 'content' containing the answer
        result = response.text
        return jsonify({'response': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/scrape_hashtag/<hashtag>', methods=['GET'])
def scrape_hashtag(hashtag):
    print(hashtag)
    max_tweets = request.args.get('max_tweets', default=50, type=int)
    
    scraper = Twitter_Scraper(
        mail=MAIL,
        username=USER_UNAME,
        password=USER_PASSWORD,
        max_tweets=max_tweets,
        scrape_hashtag=hashtag
    )
    
    scraper.login()
    scraper.scrape_tweets()
    tweets = scraper.get_tweets()
    scraper.driver.close()
    
    return jsonify(tweets)

if __name__ == '__main__':
    app.run(debug=True)
