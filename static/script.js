function searchSubreddits() {
    const topic = document.getElementById('topicInput').value;
    fetch('/search_subreddits', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({topic: topic}),
    })
    .then(response => response.json())
    .then(data => {
        const subredditList = document.getElementById('subredditList');
        subredditList.innerHTML = '<h2>Subreddits:</h2>';
        data.forEach(sub => {
            const button = document.createElement('button');
            button.textContent = sub.name;
            button.onclick = () => getPosts(sub.name);
            subredditList.appendChild(button);
        });
    });
}

function getPosts(subreddit) {
    fetch('/get_posts', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({subreddit: subreddit}),
    })
    .then(response => response.json())
    .then(data => {
        const postList = document.getElementById('postList');
        postList.innerHTML = '<h2>Posts:</h2>';
        data.forEach(post => {
            const button = document.createElement('button');
            button.textContent = `[${post.type}] ${post.title}`;
            button.onclick = () => analyzePost(post.id);
            postList.appendChild(button);
        });
    })
    .catch(error => console.error('Error:', error));
}

function analyzePost(postId) {
    console.log("Analyzing post with ID:", postId);
    fetch('/analyze_post', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({post_id: postId}),
    })
    .then(response => response.json())
    .then(data => {
        const analysisResult = document.getElementById('analysisResult');
        analysisResult.innerHTML = '<h2>Analysis:</h2><pre>' + data.analysis + '</pre>';
    })
    .catch(error => console.error('Error:', error));
}