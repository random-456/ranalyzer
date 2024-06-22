function showLoading(elementId) {
    document.getElementById(elementId).innerHTML = '<div class="d-flex justify-content-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
}

function showError(elementId, message) {
    document.getElementById(elementId).innerHTML = `<div class="alert alert-danger" role="alert">${message}</div>`;
}

function openAccordionItem(itemId) {
    const accordionItem = document.querySelector(`#${itemId}`);
    const bootstrapCollapse = new bootstrap.Collapse(accordionItem, {
        toggle: false
    });
    bootstrapCollapse.show();
}

function closeAccordionItem(itemId) {
    const accordionItem = document.querySelector(`#${itemId}`);
    const bootstrapCollapse = new bootstrap.Collapse(accordionItem, {
        toggle: false
    });
    bootstrapCollapse.hide();
}

function searchSubreddits() {
    const topic = document.getElementById('topicInput').value;
    showLoading('subredditList');
    openAccordionItem('collapseSubreddit');
    closeAccordionItem('collapseTopic');
    
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
        subredditList.innerHTML = '';
        
        const analysis = JSON.parse(data.analysis);
        
        ['most_relevant', 'maybe_relevant', 'not_relevant'].forEach(category => {
            if (analysis[category] && analysis[category].length > 0) {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'category';
                categoryDiv.innerHTML = `<h3>${category.replace('_', ' ').charAt(0).toUpperCase() + category.slice(1)}:</h3>`;
                analysis[category].forEach(sub => {
                    const button = document.createElement('button');
                    button.className = 'btn btn-outline-primary item-button';
                    button.textContent = sub.name;
                    button.onclick = () => getPosts(sub.name);
                    categoryDiv.appendChild(button);
                    const reason = document.createElement('p');
                    reason.className = 'item-reason';
                    reason.textContent = sub.reason;
                    categoryDiv.appendChild(reason);
                });
                subredditList.appendChild(categoryDiv);
            }
        });
    })
    .catch(error => showError('subredditList', 'Failed to fetch subreddits. Please try again.'));
}

function getPosts(subreddit) {
    showLoading('postList');
    openAccordionItem('collapsePost');
    closeAccordionItem('collapseSubreddit');
    
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
        postList.innerHTML = '';
        
        const analysis = JSON.parse(data.analysis);
        
        ['maybe_relevant', 'not_relevant'].forEach(category => {
            if (analysis[category] && analysis[category].length > 0) {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'category';
                categoryDiv.innerHTML = `<h3>${category.replace('_', ' ').charAt(0).toUpperCase() + category.slice(1)}:</h3>`;
                analysis[category].forEach(post => {
                    const postInfo = data.posts.find(p => p.id === post.id);
                    if (postInfo) {
                        const button = document.createElement('button');
                        button.className = 'btn btn-outline-secondary item-button';
                        button.textContent = `[${postInfo.num_comments} comments] ${postInfo.title}`;
                        button.onclick = () => analyzePost(post.id);
                        categoryDiv.appendChild(button);
                        const reason = document.createElement('p');
                        reason.className = 'item-reason';
                        reason.textContent = post.reason;
                        categoryDiv.appendChild(reason);
                    }
                });
                postList.appendChild(categoryDiv);
            }
        });
    })
    .catch(error => showError('postList', 'Failed to fetch posts. Please try again.'));
}

function analyzePost(postId) {
    showLoading('analysisResult');
    closeAccordionItem('collapsePost');
    
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
        analysisResult.innerHTML = '<h2 class="mb-3">Analysis:</h2><pre>' + data.analysis + '</pre>';
    })
    .catch(error => showError('analysisResult', 'Failed to analyze post. Please try again.'));
}