from flask import Flask, render_template, request, jsonify
import praw
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent=os.getenv('REDDIT_USER_AGENT')
)

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search_subreddits', methods=['POST'])
def search_subreddits():
    topic = request.json['topic']
    subreddits = list(reddit.subreddits.search(topic, limit=10))
    return jsonify([{'name': sub.display_name, 'title': sub.title} for sub in subreddits])

@app.route('/get_posts', methods=['POST'])
def get_posts():
    subreddit_name = request.json['subreddit']
    posts = list(reddit.subreddit(subreddit_name).hot(limit=25))
    return jsonify([{
        'title': post.title, 
        'id': post.id,
        'type': 'text' if post.is_self else 'image' if post.url.endswith(('.jpg', '.jpeg', '.png', '.gif')) else 'video' if post.is_video else 'link'
    } for post in posts])

@app.route('/analyze_post', methods=['POST'])
def analyze_post():
    print("Received data:", request.json)  # Debug print
    try:
        post_id = request.json['post_id']
    except KeyError:
        return jsonify({'error': 'Missing post_id in request'}), 400
    
    submission = reddit.submission(id=post_id)
    
    # Prepare the content based on the type of post
    content = f"Title: {submission.title}\n\n"
    
    if submission.is_self:
        # Text post
        content += f"Content: {submission.selftext}"
    elif submission.is_video:
        # Video post
        content += f"Content: This is a video post. Video URL: {submission.url}"
    elif submission.url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
        # Image post
        content += f"Content: This is an image post. Image URL: {submission.url}"
    else:
        # Link post
        content += f"Content: This is a link post. Link: {submission.url}"
    
    # Fetch comments
    submission.comments.replace_more(limit=None)
    comments = [comment.body for comment in submission.comments.list()[:10]]  # Limit to first 10 comments
    full_content = content + "\n\nComments:\n" + "\n\n".join(comments)

    system_message = "You are an assistant that analyzes reddit posts and their comments in order to detect and understand potential problems that people have and derive business models from it. I will provide the post title, content (which may be text, an image description, or a link), and the comments to you, and you need to evaluate if this is a potential problem which can be solved by a business model which can be launched by me. If it is not the case, you simply answer 'No potential business model detected'. You do not have to make up impractical ideas which make no sense but instead be strict and just refuse an answer if you do not see any potential business model. However, if you see a potential business model related to the content I provide you with, you will need to explain it very detailed."

    completion = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": full_content}
        ]
    )
    analysis = completion.choices[0].message.content
    return jsonify({'analysis': analysis})

if __name__ == '__main__':
    app.run(debug=True)