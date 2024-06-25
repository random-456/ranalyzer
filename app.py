import os
import time
from flask import Flask, render_template, request, jsonify, session
import praw
from prawcore.exceptions import PrawcoreException
from openai import OpenAI
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import uuid
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key')  # for session management

# MySQL Configuration
db_config = {
    'host': os.getenv('MYSQL_HOST'),
    'database': os.getenv('MYSQL_DBNAME'),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD')
}

reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent=os.getenv('REDDIT_USER_AGENT')
)

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def create_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
    return None

def save_analysis(user_id, topic, subreddit, post_id, post_title, analysis, business_model_title):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = """INSERT INTO analysis_results 
                       (user_id, topic, subreddit, post_id, post_title, analysis, business_model_title) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(query, (user_id, topic, subreddit, post_id, post_title, analysis, business_model_title))
            connection.commit()
        except Error as e:
            print(f"Error while saving analysis: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()


def get_user_profile_data(user_id):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM user_profiles WHERE user_id = %s"
            cursor.execute(query, (user_id,))
            profile = cursor.fetchone()
            return profile if profile else {}
        except Error as e:
            print(f"Error while fetching user profile: {e}")
            return {}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return {}

@app.route('/')
def index():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())  # Generate a unique ID for the session
    return render_template('index.html')

@app.route('/search_subreddits', methods=['POST'])
def search_subreddits():
    topic = request.json['topic']
    user_id = session.get('user_id', 'anonymous')
    
    reddit_requests_count = 1  # Count for the subreddit search
    subreddits = list(reddit.subreddits.search(topic, limit=10))
    log_api_request('reddit', user_id, None, None, reddit_requests_count, "Search subreddits")
    
    subreddit_info = [{
        'name': sub.display_name,
        'description': sub.public_description,
        'subscribers': sub.subscribers
    } for sub in subreddits]
    
    # Analyze subreddits with OpenAI
    system_message = """
    You are an assistant that analyzes subreddits to determine their relevance to a given topic.
    You will receive a topic and a list of subreddits with their descriptions.
    Your task is to sort these subreddits into three categories: Most relevant, Maybe relevant, and Less relevant.
    Provide your response in the following JSON format:
    {
        "most_relevant": [{"name": "subreddit_name", "reason": "brief explanation"}],
        "maybe_relevant": [{"name": "subreddit_name", "reason": "brief explanation"}],
        "not_relevant": [{"name": "subreddit_name", "reason": "brief explanation"}]
    }
    """
    
    user_message = f"Topic: {topic}\nSubreddits:\n" + "\n".join([f"{sub['name']}: {sub['description']}" for sub in subreddit_info])
    
    completion = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
    )
    
    tokens_used = completion.usage.total_tokens
    log_api_request('openai', user_id, 'gpt-3.5-turbo', tokens_used, None, "Analyze subreddits")
    
    analysis = completion.choices[0].message.content
    return jsonify({'subreddits': subreddit_info, 'analysis': analysis})

@app.route('/get_posts', methods=['POST'])
def get_posts():
    subreddit_name = request.json['subreddit']
    user_id = session.get('user_id', 'anonymous')
    
    reddit_requests_count = 1  # Count for fetching hot posts
    posts = list(reddit.subreddit(subreddit_name).hot(limit=100))
    log_api_request('reddit', user_id, None, None, reddit_requests_count, f"Get posts from r/{subreddit_name}")
    
    posts_with_comments = [post for post in posts if post.num_comments > 0][:25]
    
    post_info = [{
        'id': post.id,
        'title': post.title,
        'num_comments': post.num_comments
    } for post in posts_with_comments]
    
    # Analyze posts with OpenAI
    system_message = """
You are an assistant that analyzes Reddit post titles to determine their potential for containing business ideas.
You will receive a list of post titles. Your task is to categorize these posts into two groups: Maybe relevant and Maybe less relevant.
Provide your response in the following JSON format:
{
    "maybe_relevant": [{"id": "post_id", "reason": "brief explanation"}],
    "not_relevant": [{"id": "post_id", "reason": "brief explanation"}]
}
"""
    
    user_message = "Post titles:\n" + "\n".join([f"{post['id']}: {post['title']}" for post in post_info])
    
    completion = openai_client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]
)
    tokens_used = completion.usage.total_tokens
    log_api_request('openai', user_id, 'gpt-3.5-turbo', tokens_used, None, "Analyze posts")
    
    analysis = completion.choices[0].message.content
    return jsonify({'posts': post_info, 'analysis': analysis})

@app.route('/analyze_post', methods=['POST'])
def analyze_post():
    post_id = request.json['post_id']
    topic = request.json.get('topic', '')
    subreddit = request.json.get('subreddit', '')
    user_id = session.get('user_id', 'anonymous')
    
    reddit_requests_count = 1  # Count for fetching the submission
    submission = reddit.submission(id=post_id)
    
    content = f"Title: {submission.title}\n\n"
    
    if submission.is_self:
        content += f"Content: {submission.selftext}"
    elif submission.is_video:
        content += f"Content: This is a video post. Video URL: {submission.url}"
    elif submission.url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
        content += f"Content: This is an image post. Image URL: {submission.url}"
    else:
        content += f"Content: This is a link post. Link: {submission.url}"
    
    submission.comments.replace_more(limit=None)
    reddit_requests_count += 1  # Increment for replace_more()
    comments = [comment.body for comment in submission.comments.list()[:10]]
    
    log_api_request('reddit', user_id, None, None, reddit_requests_count, f"Analyze post {post_id}")
    
    full_content = content + "\n\nComments:\n" + "\n\n".join(comments)

    system_message = f"""You are an assistant that analyzes reddit posts and their comments to detect and understand potential problems that people have and derive business models from them. I will provide the post title, content (which may be text, an image description, or a link), and the comments to you.

    Your task is to:
    1. Evaluate if there is a potential problem or need expressed in the post or comments that could be addressed by a business model.
    2. If you detect a potential business opportunity, you MUST provide a detailed explanation of the business model idea in the following JSON format:
       {{
         "business_model_title": "A short, descriptive title for the business model (max 50 characters)",
         "problem_identified": "Description of the problem or need",
         "proposed_solution": "Detailed explanation of the proposed solution",
         "target_market": "Description of the target market",
         "potential_revenue_streams": "List of potential revenue streams",
         "challenges_or_considerations": "List of challenges or considerations for implementing this business model",
         "market_entry_difficulty": "Assessment of how easy or hard it is to develop a product and enter the market",
         "alignment_with_user_profile": "Explanation of how well this business idea aligns with the user's profile"
       }}

    If you do not see any viable business opportunity, respond with:
    {{
      "business_model_title": "No viable business model",
      "analysis": "No potential business model detected",
      "reason": "Brief explanation why no viable opportunity was identified"
    }}

    Remember, only suggest practical and ethical business ideas that align with the user's profile. Do not invent or assume information not present in the provided content."""


    completion = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": full_content}
        ]
    )
    analysis = completion.choices[0].message.content
    tokens_used = completion.usage.total_tokens
    log_api_request('openai', user_id, 'gpt-3.5-turbo', tokens_used, None, "Analyze post")
    analysis_json = json.loads(analysis)
    business_model_title = analysis_json.get('business_model_title', 'Untitled Business Model')

    # Save the analysis to the database
    save_analysis(user_id, topic, subreddit, post_id, submission.title, analysis, business_model_title)
    
    return jsonify({'analysis': analysis})


@app.route('/get_user_profile', methods=['GET'])
def get_user_profile():
    user_id = session.get('user_id', 'anonymous')
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM user_profiles WHERE user_id = %s"
            cursor.execute(query, (user_id,))
            profile = cursor.fetchone()
            return jsonify(profile if profile else {})
        except Error as e:
            print(f"Error while fetching user profile: {e}")
            return jsonify({"error": "Failed to fetch user profile"}), 500
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

@app.route('/save_user_profile', methods=['POST'])
def save_user_profile():
    user_id = session.get('user_id', 'anonymous')
    profile_data = request.json
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = """INSERT INTO user_profiles 
                       (user_id, educational_background, professional_experience, skills, availability, other_criteria) 
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                       educational_background = VALUES(educational_background),
                       professional_experience = VALUES(professional_experience),
                       skills = VALUES(skills),
                       availability = VALUES(availability),
                       other_criteria = VALUES(other_criteria)"""
            cursor.execute(query, (user_id, profile_data['educational_background'], 
                                   profile_data['professional_experience'], profile_data['skills'],
                                   profile_data['availability'], profile_data['other_criteria']))
            connection.commit()
            return jsonify({"message": "Profile saved successfully"})
        except Error as e:
            print(f"Error while saving user profile: {e}")
            return jsonify({"error": "Failed to save user profile"}), 500
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()


@app.route('/generate_topics', methods=['GET'])
def generate_topics():
    user_id = session.get('user_id', 'anonymous')
    user_profile = get_user_profile_data(user_id)

    system_message = f"""You are an assistant that generates general topic ideas for Reddit exploration, which could potentially lead to business model insights. 
    Consider the user's profile:

    Educational Background: {user_profile.get('educational_background', 'Not specified')}
    Professional Experience: {user_profile.get('professional_experience', 'Not specified')}
    Skills: {user_profile.get('skills', 'Not specified')}
    Availability: {user_profile.get('availability', 'Not specified')}
    Other Criteria: {user_profile.get('other_criteria', 'Not specified')}

    Generate 10 unique general topic ideas that:
    1. Are likely to have dedicated subreddits
    2. Relate to everyday life, hobbies, interests, or common subjects
    3. Could potentially lead to business ideas when explored further
    4. Are tailored to the user's background and skills where possible

    IMPORTANT:
    - Each topic must be a single word, or at most two words if absolutely necessary
    - Topics should be general and widely recognizable
    - Avoid specialized jargon or overly niche terms
    - Think of subjects that average people discuss or are interested in

    Examples of good topics: fishing, cars, weddings, pets, cooking, fitness, travel, books, movies, gardening

    Provide your response in the following JSON format:
    {{
        "topics": ["topic1", "topic2", "topic3", ...]
    }}
    Remember, each topic should be a single word where possible, and never more than two words."""

    try:
        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": "Generate general topic ideas for Reddit exploration."}
            ]
        )

        content = completion.choices[0].message.content
        tokens_used = completion.usage.total_tokens
        log_api_request('openai', user_id, 'gpt-3.5-turbo', tokens_used, None, "Generate topics")

        try:
            topics = json.loads(content)
            # Ensure topics are no more than 2 words
            topics['topics'] = [' '.join(topic.split()[:2]) for topic in topics['topics']]
            return jsonify(topics)
        except ValueError as e:
            print(f"Failed to parse JSON: {content}")
            return jsonify({"error": "Failed to parse topics", "raw_content": content}), 500
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@app.route('/saved_analyses')
def saved_analyses():
    user_id = session.get('user_id', 'anonymous')
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """SELECT id, topic, subreddit, post_id, post_title, business_model_title, analysis, created_at 
                       FROM analysis_results 
                       WHERE user_id = %s 
                       ORDER BY created_at DESC"""
            cursor.execute(query, (user_id,))
            analyses = cursor.fetchall()
            return render_template('saved_analyses.html', analyses=analyses)
        except Error as e:
            print(f"Error while fetching saved analyses: {e}")
            return jsonify({"error": "Failed to fetch saved analyses"}), 500
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return jsonify({"error": "Database connection failed"}), 500


def log_api_request(api_type, user_id=None, openai_model=None, openai_tokens_used=None, reddit_requests_count=None, additional_info=None):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = """INSERT INTO api_request_logs 
                       (api_type, user_id, openai_model, openai_tokens_used, reddit_requests_count, additional_info) 
                       VALUES (%s, %s, %s, %s, %s, %s)"""
            cursor.execute(query, (api_type, user_id, openai_model, openai_tokens_used, reddit_requests_count, additional_info))
            connection.commit()
        except Error as e:
            print(f"Error logging API request: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()


@app.template_filter('from_json')
def from_json(value):
    return json.loads(value)


if __name__ == '__main__':
    app.run(debug=True)