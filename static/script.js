let currentTopic = '';

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
    currentTopic = document.getElementById('topicInput').value;
    showLoading('subredditList');
    openAccordionItem('collapseSubreddit');
    closeAccordionItem('collapseTopic');
    
    fetch('/search_subreddits', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({topic: currentTopic}),
    })
    .then(response => response.json())
    .then(data => {
        const subredditList = document.getElementById('subredditList');
        subredditList.innerHTML = '';
        
        const analysis = JSON.parse(data.analysis);
        
        const categories = {
            'most_relevant': 'Most relevant',
            'maybe_relevant': 'Maybe relevant',
            'not_relevant': 'Less relevant'
        };
        
        Object.entries(categories).forEach(([key, title]) => {
            if (analysis[key] && analysis[key].length > 0) {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'category';
                categoryDiv.innerHTML = `<h3>${title}</h3>`;
                analysis[key].forEach(sub => {
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
    currentSubreddit = subreddit;
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
        
        const categories = {
            'maybe_relevant': 'Maybe relevant',
            'not_relevant': 'Maybe less relevant'
        };
        
        Object.entries(categories).forEach(([key, title]) => {
            if (analysis[key] && analysis[key].length > 0) {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'category';
                categoryDiv.innerHTML = `<h3>${title}</h3>`;
                analysis[key].forEach(post => {
                    const postInfo = data.posts.find(p => p.id === post.id);
                    if (postInfo) {
                        const postDiv = document.createElement('div');
                        postDiv.className = 'post-item';
                        
                        const button = document.createElement('button');
                        button.className = 'btn btn-outline-secondary item-button';
                        button.textContent = postInfo.title;
                        button.onclick = () => analyzePost(post.id);
                        
                        const commentCount = document.createElement('p');
                        commentCount.className = 'comment-count';
                        commentCount.innerHTML = `<strong>${postInfo.num_comments}</strong> comments`;
                        
                        const reason = document.createElement('p');
                        reason.className = 'item-reason';
                        reason.textContent = post.reason;
                        
                        postDiv.appendChild(commentCount);
                        postDiv.appendChild(button);
                        postDiv.appendChild(reason);
                        categoryDiv.appendChild(postDiv);
                    }
                });
                postList.appendChild(categoryDiv);
            }
        });
    })
    .catch(error => showError('postList', 'Failed to fetch posts. Please try again.'));
}

function analyzePost(postId) {
    console.log(`Analyzing post: ${postId}, Topic: ${currentTopic}, Subreddit: ${currentSubreddit}`);
    showLoading('analysisResult');
    
    fetch('/analyze_post', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            post_id: postId,
            topic: currentTopic,
            subreddit: currentSubreddit
        }),
    })
    .then(response => {
        console.log('Response received:', response);
        return response.json();
    })
    .then(data => {
        console.log('Analysis data:', data);
        const analysisResult = document.getElementById('analysisResult');
        let formattedAnalysis = '<h2 class="mb-3">Analysis</h2>';
        
        try {
            const analysis = JSON.parse(data.analysis);
            if (analysis.analysis === "No potential business model detected") {
                formattedAnalysis += `<p><strong>Result:</strong> ${analysis.analysis}</p>`;
                formattedAnalysis += `<p><strong>Reason:</strong> ${analysis.reason}</p>`;
            } else {
                const sections = [
                    { key: 'problem_identified', title: 'Problem Identified' },
                    { key: 'proposed_solution', title: 'Proposed Solution' },
                    { key: 'target_market', title: 'Target Market' },
                    { key: 'potential_revenue_streams', title: 'Potential Revenue Streams' },
                    { key: 'challenges_or_considerations', title: 'Challenges or Considerations' },
                    { key: 'market_entry_difficulty', title: 'Market Entry Difficulty' }
                ];

                sections.forEach(section => {
                    if (analysis[section.key]) {
                        formattedAnalysis += `<h3>${section.title}</h3>`;
                        formattedAnalysis += `<p>${analysis[section.key]}</p>`;
                    }
                });
            }
        } catch (error) {
            console.error('Error parsing analysis:', error);
            formattedAnalysis += '<p>Error: Unable to parse analysis result.</p>';
        }
        
        analysisResult.innerHTML = formattedAnalysis;
    })
    .catch(error => {
        console.error('Error during analysis:', error);
        showError('analysisResult', 'Failed to analyze post. Please try again.');
    });
}