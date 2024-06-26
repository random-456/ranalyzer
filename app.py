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
from celery import Celery
import celery_config
import redis

load_dotenv()



# Test Redis connection
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    redis_client.ping()
    print("Successfully connected to Redis")
except redis.ConnectionError:
    print("Failed to connect to Redis")

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key')  # for session management
app.config['broker_url'] = 'redis://localhost:6379/0'
app.config['result_backend'] = 'redis://localhost:6379/0'

celery = Celery(app.name)
celery.conf.update(app.config)


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

def save_analysis(user_id, topic, subreddit, post_id, post_title, analysis, business_model_title, job_id=None):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            analysis_id = str(uuid.uuid4())  # Generate a new analysis_id
            print(f"New analysis id: {analysis_id}")
            query = """INSERT INTO analysis_results 
                       (id, user_id, topic, subreddit, post_id, post_title, analysis, business_model_title, job_id) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            values = (analysis_id, user_id, topic, subreddit, post_id, post_title, analysis, business_model_title, job_id)
            print(f"Attempting to insert with values: {values}")  # Debug print
            cursor.execute(query, values)
            connection.commit()
            print(f"Successfully saved analysis with ID: {analysis_id}, job_id: {job_id}")  # Debug print
            return analysis_id
        except mysql.connector.IntegrityError as e:
            print(f"IntegrityError: {e}")
            print(f"Error code: {e.errno}")
            print(f"SQL State: {e.sqlstate}")
            print(f"Message: {e.msg}")
            if e.errno == 1062:  # Duplicate entry
                # Try to update instead
                update_query = """UPDATE analysis_results 
                                  SET topic = %s, subreddit = %s, post_title = %s, analysis = %s, 
                                      business_model_title = %s, job_id = %s
                                  WHERE user_id = %s AND post_id = %s"""
                update_values = (topic, subreddit, post_title, analysis, business_model_title, job_id, user_id, post_id)
                cursor.execute(update_query, update_values)
                connection.commit()
                print(f"Updated existing analysis for user_id: {user_id}, post_id: {post_id}")
                return post_id  # Return post_id as identifier for updated row
        except Error as e:
            print(f"Error while saving analysis: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return None


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
        session['user_id'] = str(uuid.uuid4())
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
    user_id = request.json.get('user_id', session.get('user_id', 'anonymous'))
    job_id = request.json.get('job_id', None)
    
    analysis = analyze_post_internal(post_id, topic, subreddit, user_id, job_id)
    
    return jsonify({'analysis': analysis})


def analyze_post_internal(post_id, topic, subreddit, user_id, job_id=None):
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
    
    log_api_request('reddit', user_id, None, None, reddit_requests_count, f"Retrieve post {post_id}")
    
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

    print(f"Analyzing post {post_id} for job {job_id}")  # Debug print
    completion = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": full_content}
        ]
    )
    try:
        analysis = completion.choices[0].message.content
        tokens_used = completion.usage.total_tokens
        log_api_request('openai', user_id, 'gpt-3.5-turbo', tokens_used, None, "Analyze post")
        
        analysis_json = json.loads(analysis)
        business_model_title = analysis_json.get('business_model_title', 'Untitled Business Model')
    except json.JSONDecodeError:
        print(f"Error decoding JSON for post {post_id}: {analysis}")
        business_model_title = 'Error in Analysis'
        analysis = json.dumps({"error": "Failed to parse analysis"})
    except Exception as e:
        print(f"Unexpected error processing analysis for post {post_id}: {str(e)}")
        business_model_title = 'Error in Analysis'
        analysis = json.dumps({"error": "Unexpected error during analysis"})

    # Save the analysis to the database
    print(f"Saving analysis for post {post_id} with job ID {job_id}")  # Debug print
    analysis_id = save_analysis(
        user_id=user_id,
        topic=topic,
        subreddit=subreddit,
        post_id=post_id,
        post_title=submission.title,
        analysis=analysis,
        business_model_title=business_model_title,
        job_id=job_id
    )
    
    if analysis_id:
        print(f"Successfully saved analysis for post {post_id} with ID {analysis_id}")
    else:
        print(f"Failed to save analysis for post {post_id}")

    return analysis


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
    - Each topic MUST be a single word, do NOT glue words together to cheat. E.g. instead fitnessworkouts just fitness. Keep it short.
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


@celery.task(bind=True)
def perform_mass_analysis(self, job_id, user_id, subreddit, num_posts):
    print(f"Starting mass analysis for job {job_id}")
    job = update_job_status(job_id, 'in_progress')
    
    posts = get_unanalyzed_posts(user_id, subreddit, num_posts)
    print(f"Found {len(posts)} unanalyzed posts")
    for i, post in enumerate(posts):
        try:
            analyze_post_internal(post.id, '', subreddit, user_id, job_id=job_id)
            update_job_progress(job_id, i + 1)
            print(f"Analyzed post {i+1}/{len(posts)} for job {job_id}")
        except Exception as e:
            print(f"Error analyzing post {post.id} for job {job_id}: {str(e)}")
    
    update_job_status(job_id, 'completed')
    print(f"Completed mass analysis for job {job_id}")


@app.route('/start_mass_analysis', methods=['POST'])
def start_mass_analysis():
    try:
        app.logger.info("start_mass_analysis called")
        user_id = session.get('user_id', 'anonymous')
        app.logger.info(f"User ID: {user_id}")
        subreddit = request.json['subreddit']
        app.logger.info(f"Subreddit: {subreddit}")
        num_posts = int(request.json['num_posts'])
        app.logger.info(f"Number of posts: {num_posts}")
        
        job_id = create_mass_analysis_job(user_id, subreddit, num_posts)
        app.logger.info(f"Created job with ID: {job_id}")
        if job_id is None:
            app.logger.error("Failed to create job")
            return jsonify({'error': 'Failed to create job'}), 500
        
        perform_mass_analysis.delay(job_id, user_id, subreddit, num_posts)
        app.logger.info(f"Started mass analysis task for job {job_id}")
        
        return jsonify({'job_id': job_id})
    except Exception as e:
        app.logger.error(f"Error in start_mass_analysis: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/get_job_status/<int:job_id>')
def get_job_status(job_id):
    job = get_job_by_id(job_id)
    return jsonify(job)

@app.route('/mass_analysis_jobs')
def mass_analysis_jobs():
    user_id = session.get('user_id', 'anonymous')
    jobs = get_user_jobs(user_id)
    return render_template('mass_analysis_jobs.html', jobs=jobs)

@app.route('/job_results/<int:job_id>')
def job_results(job_id):
    analyses = get_job_analyses(job_id)
    return render_template('job_results.html', analyses=analyses)


@app.template_filter('from_json')
def from_json(value):
    return json.loads(value)

@celery.task
def update_job_statuses():
    # Update status of all in-progress jobs
    pass

celery.conf.beat_schedule = {
    'update-job-statuses-every-minute': {
        'task': 'app.update_job_statuses',
        'schedule': 60.0,
    },
}


def create_mass_analysis_job(user_id, subreddit, num_posts):
    connection = None
    try:
        connection = create_db_connection()
        if connection:
            cursor = connection.cursor()
            job_id = str(uuid.uuid4())
            query = """INSERT INTO mass_analysis_jobs 
                       (id, user_id, subreddit, total_posts, status) 
                       VALUES (%s, %s, %s, %s, %s)"""
            cursor.execute(query, (job_id, user_id, subreddit, num_posts, 'pending'))
            connection.commit()
            return job_id
        else:
            app.logger.error("Failed to create database connection")
            return None
    except Error as e:
        app.logger.error(f"Error creating mass analysis job: {e}", exc_info=True)
        return None
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def update_job_status(job_id, status):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = """UPDATE mass_analysis_jobs 
                       SET status = %s
                       WHERE id = %s"""
            cursor.execute(query, (status, job_id))
            connection.commit()
        except Error as e:
            print(f"Error updating job status: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

def update_job_progress(job_id, completed_posts):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = """UPDATE mass_analysis_jobs 
                       SET completed_posts = %s
                       WHERE id = %s"""
            cursor.execute(query, (completed_posts, job_id))
            connection.commit()
        except Error as e:
            print(f"Error updating job progress: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

def get_unanalyzed_posts(user_id, subreddit, num_posts):
    analyzed_posts = set()
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = """SELECT post_id FROM analysis_results 
                       WHERE user_id = %s AND subreddit = %s"""
            cursor.execute(query, (user_id, subreddit))
            analyzed_posts = set(row[0] for row in cursor.fetchall())
        except Error as e:
            print(f"Error fetching analyzed posts: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    subreddit_instance = reddit.subreddit(subreddit)
    unanalyzed_posts = []
    for post in subreddit_instance.new(limit=None):
        if post.id not in analyzed_posts:
            unanalyzed_posts.append(post)
            if len(unanalyzed_posts) == num_posts:
                break
    return unanalyzed_posts

def get_job_by_id(job_id):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """SELECT * FROM mass_analysis_jobs 
                       WHERE id = %s"""
            cursor.execute(query, (job_id,))
            return cursor.fetchone()
        except Error as e:
            print(f"Error fetching job: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return None

def get_user_jobs(user_id):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """SELECT * FROM mass_analysis_jobs 
                       WHERE user_id = %s
                       ORDER BY created_at DESC"""
            cursor.execute(query, (user_id,))
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching user jobs: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return []

def get_job_analyses(job_id):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """SELECT * FROM analysis_results 
                       WHERE job_id = %s"""
            cursor.execute(query, (job_id,))
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching job analyses: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return []


@app.route('/analyses')
def analysis_list():
    user_id = session.get('user_id', 'anonymous')
    source = request.args.get('source', 'saved')
    job_id = request.args.get('job_id')
    
    if source == 'job' and job_id:
        analyses = get_job_analyses(job_id)
        title = f"Job #{job_id} Results"
    else:
        analyses = get_saved_analyses(user_id)
        title = "Your Saved Analyses"
    
    return render_template('analysis_list.html', analyses=analyses, title=title)

@app.route('/analysis/<string:analysis_id>')
def analysis_detail(analysis_id):
    analysis = get_analysis_by_id(analysis_id)
    source = request.args.get('source', 'saved')
    job_id = request.args.get('job_id')
    return render_template('analysis_detail.html', analysis=analysis, source=source, job_id=job_id)


def get_saved_analyses(user_id):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """SELECT id, topic, subreddit, post_id, post_title, business_model_title, analysis, created_at 
                       FROM analysis_results 
                       WHERE user_id = %s AND job_id IS NULL
                       ORDER BY created_at DESC"""
            cursor.execute(query, (user_id,))
            analyses = cursor.fetchall()
            return analyses
        except Error as e:
            print(f"Error while fetching saved analyses: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return []

def get_job_analyses(job_id):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """SELECT id, topic, subreddit, post_id, post_title, business_model_title, analysis, created_at 
                       FROM analysis_results 
                       WHERE job_id = %s
                       ORDER BY created_at DESC"""
            cursor.execute(query, (job_id,))
            analyses = cursor.fetchall()
            return analyses
        except Error as e:
            print(f"Error while fetching job analyses: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return []

def get_analysis_by_id(analysis_id):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """SELECT id, topic, subreddit, post_id, post_title, business_model_title, analysis, created_at, job_id
                       FROM analysis_results 
                       WHERE id = %s"""
            cursor.execute(query, (analysis_id,))
            analysis = cursor.fetchone()
            return analysis
        except Error as e:
            print(f"Error while fetching analysis by ID: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return None


if __name__ == '__main__':
    app.run(debug=True)