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
    subreddit_info = [{'name': sub.display_name, 'description': sub.public_description} for sub in subreddits]
    
    # Analyze subreddits with OpenAI
    system_message = """
    You are an assistant that analyzes subreddits to determine their relevance to a given topic.
    You will receive a topic and a list of subreddits with their descriptions.
    Your task is to sort these subreddits into three categories: Most relevant, Maybe relevant, and Not relevant.
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
    
    analysis = completion.choices[0].message.content
    return jsonify({'subreddits': subreddit_info, 'analysis': analysis})

@app.route('/get_posts', methods=['POST'])
def get_posts():
    subreddit_name = request.json['subreddit']
    posts = list(reddit.subreddit(subreddit_name).hot(limit=100))  # Fetch more to ensure we get 25 with comments
    posts_with_comments = [post for post in posts if post.num_comments > 0][:25]
    
    post_info = [{
        'id': post.id,
        'title': post.title,
        'num_comments': post.num_comments
    } for post in posts_with_comments]
    
    # Analyze posts with OpenAI
    system_message = """
    You are an assistant that analyzes Reddit post titles to determine their potential for containing business ideas.
    You will receive a list of post titles. Your task is to categorize these posts into two groups: Maybe relevant and Not relevant.
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
    
    analysis = completion.choices[0].message.content
    return jsonify({'posts': post_info, 'analysis': analysis})

@app.route('/analyze_post', methods=['POST'])
def analyze_post():
    post_id = request.json['post_id']
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
    comments = [comment.body for comment in submission.comments.list()[:10]]
    full_content = content + "\n\nComments:\n" + "\n\n".join(comments)

    system_message = """You are an assistant that analyzes reddit posts and their comments in order to detect and understand potential problems that people have and derive business models from it. I will provide the post title, content (which may be text, an image description, or a link), and the comments to you, and you need to evaluate if this is a potential problem which can be solved by a business model which can be launched by me. If it is not the case, you simply answer 'No potential business model detected'. You do not have to make up impractical ideas which make no sense but instead be strict and just refuse an answer if you do not see any potential business model. However, if you see a potential business model related to the content I provide you with, you will need to explain it very detailed."""

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