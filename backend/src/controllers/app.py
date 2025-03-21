import sys
import logging
import os
import json
import random
from scholarly import scholarly
from sentence_transformers import SentenceTransformer, util
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Suppress all gRPC logs and unnecessary warnings
os.environ["GRPC_VERBOSITY"] = "NONE"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# Configure logging to print debug messages to stderr
logging.basicConfig(
    filename='app.log',  # Log file name
    level=logging.INFO,  # Log level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize the SentenceTransformer model
try:
    logging.info("Initializing SentenceTransformer model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    logging.info("SentenceTransformer model initialized successfully!")
except Exception as e:
    print(json.dumps({"error": f"Error initializing SentenceTransformer: {str(e)}"}))
    sys.exit()

def fetch_book_details(title):
    """
    Fetch book details from the Google Books API using the title.
    """
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": f"intitle:{title}",  # Search by title
        "key": os.getenv("GEMINI_API_KEY")  # Use the API key from .env
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()  # Return the JSON response from the API
    else:
        logging.error(f"Error fetching book details: {response.status_code}")
        return None

def suggest_better_title(title):
    """
    Generate a better title suggestion based on the input title.
    """
    # Split the title into keywords
    keywords = title.split()

    # Define some templates for rephrasing
    templates = [
        "A Study of {keywords} in {main_topic}",
        "Exploring {keywords} in {main_topic}",
        "An Analysis of {keywords} in {main_topic}",
        "{keywords}: A New Perspective on {main_topic}",
        "{main_topic} and the Role of {keywords}"
    ]

    # Identify the main topic (e.g., the last keyword or phrase)
    main_topic = keywords[-1]  # Example: "Gatsby" from "The Great Gatsby"

    # Randomly select a template
    template = random.choice(templates)

    # Generate the suggested title
    suggested_title = template.format(
        keywords=" ".join(keywords[:-1]),  # All keywords except the last
        main_topic=main_topic
    )

    return suggested_title

def analyze_title_with_book_api(title, reason):
    """
    Analyze the title using the Book API and suggest a better title.
    """
    book_details = fetch_book_details(title)
    if not book_details:
        return "No book details found."

    # Extract relevant details from the API response
    items = book_details.get("items", [])
    if not items:
        return "No matching books found."

    # Use the first book in the results
    book_info = items[0]["volumeInfo"]
    book_title = book_info.get("title", "N/A")
    authors = ", ".join(book_info.get("authors", ["N/A"]))
    published_date = book_info.get("publishedDate", "N/A")

    # Generate feedback
    feedback = f"Book Title: {book_title}\n"
    feedback += f"Author(s): {authors}\n"
    feedback += f"Publication Year: {published_date}\n"
    feedback += f"Similarity: {reason}\n"

    # Suggest a better title
    suggested_title = suggest_better_title(title)
    feedback += f"Suggested Title: {suggested_title}\n"

    return feedback

def fetch_top_results(query, num_results=5):
    logging.info(f"Fetching top results for query: '{query}'...")
    search_query = scholarly.search_pubs(query)
    results = []
    for _ in range(num_results):
        try:
            result = next(search_query)
            title = result['bib']['title']
            pub_url = result.get('pub_url', 'No link available')
            results.append({"title": title, "url": pub_url})
        except StopIteration:
            logging.info("No more results found.")
            break
    logging.info(f"Fetched {len(results)} results.")
    return results

def analyze_uniqueness(submitted_title, search_results):
    logging.info("Analyzing uniqueness of the title...")
    if not search_results:
        logging.info("No search results found.")
        return {
            "input": submitted_title,
            "output": {
                "queried_title": "N/A",
                "feedback": "No search results found. This title appears to be unique and doesn't match any existing publications.",
                "approval_probability": 100.0
            }
        }

    query_embedding = model.encode(submitted_title, convert_to_tensor=True)
    titles = [result['title'] for result in search_results]
    title_embeddings = model.encode(titles, convert_to_tensor=True)

    similarity_scores = util.pytorch_cos_sim(query_embedding, title_embeddings)[0]

    for idx, (result, score) in enumerate(zip(search_results, similarity_scores)):
        score = score.item()
        if score == 1.0:
            feedback = analyze_title_with_book_api(submitted_title, f"Duplicate of '{result['title']}'.")
            return {
                "input": submitted_title,
                "output": {
                    "queried_title": result['title'],
                    "feedback": feedback,
                    "approval_probability": 0.0
                }
            }

    best_match_idx = similarity_scores.argmax().item()
    best_match_score = similarity_scores[best_match_idx].item()

    if best_match_score >= 0.75:  # Lower the threshold
        reason = f"highly similar to '{titles[best_match_idx]}', similarity score: {best_match_score:.2f}"
    else:
        reason = "unique"

    feedback = analyze_title_with_book_api(submitted_title, reason)
    approval_probability = (1 - best_match_score) * 100

    return {
        "input": submitted_title,
        "output": {
            "queried_title": titles[best_match_idx],
            "feedback": feedback,
            "approval_probability": approval_probability
        }
    }

def main():
    logging.info("Starting script...")
    submitted_title = sys.stdin.read().strip()

    if not submitted_title:
        print(json.dumps({"error": "No title provided!"}))
        return

    logging.info(f"Submitted Title: {submitted_title}")
    search_results = fetch_top_results(submitted_title, num_results=5)
    analysis = analyze_uniqueness(submitted_title, search_results)
    print(json.dumps(analysis, indent=2))  # Only JSON is printed to stdout

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"error": f"An unexpected error occurred: {str(e)}"}))