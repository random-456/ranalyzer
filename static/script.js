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
                    const subInfo = data.subreddits.find(s => s.name === sub.name);
                    const subDiv = document.createElement('div');
                    subDiv.className = 'subreddit-item';
                    
                    const subscriberCount = document.createElement('p');
                    subscriberCount.className = 'subscriber-count';
                    subscriberCount.innerHTML = `<strong>${subInfo.subscribers.toLocaleString()}</strong> subscribers`;
                    
                    const button = document.createElement('button');
                    button.className = 'btn btn-outline-secondary item-button';
                    button.textContent = sub.name;
                    button.onclick = () => getPosts(sub.name);
                    
                    const reason = document.createElement('p');
                    reason.className = 'item-reason';
                    reason.textContent = sub.reason;
                    
                    subDiv.appendChild(subscriberCount);
                    subDiv.appendChild(button);
                    subDiv.appendChild(reason);
                    categoryDiv.appendChild(subDiv);
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
    .then(response => response.json())
    .then(data => {
        const analysisResult = document.getElementById('analysisResult');
        let formattedAnalysis = '<h2 class="mb-3">Analysis</h2>';
        
        // Add the Reddit post URL
        const postUrl = `https://www.reddit.com/comments/${postId}`;
        formattedAnalysis += `<p><strong>Original Post:</strong> <a href="${postUrl}" target="_blank">${postUrl}</a></p>`;

        
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

function loadUserProfile() {
    fetch('/get_user_profile')
        .then(response => response.json())
        .then(data => {
            if (data.educational_background) {
                document.getElementById('educationalBackground').value = data.educational_background;
                document.getElementById('professionalExperience').value = data.professional_experience;
                document.getElementById('skills').value = data.skills;
                document.getElementById('availability').value = data.availability;
                document.getElementById('otherCriteria').value = data.other_criteria;
            }
        })
        .catch(error => console.error('Error loading user profile:', error));
}

function saveUserProfile() {
    const profileData = {
        educational_background: document.getElementById('educationalBackground').value,
        professional_experience: document.getElementById('professionalExperience').value,
        skills: document.getElementById('skills').value,
        availability: document.getElementById('availability').value,
        other_criteria: document.getElementById('otherCriteria').value
    };

    fetch('/save_user_profile', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(profileData),
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            alert('Profile saved successfully!');
            $('#userProfileModal').modal('hide');
        } else {
            alert('Failed to save profile. Please try again.');
        }
    })
    .catch(error => {
        console.error('Error saving profile:', error);
        alert('An error occurred while saving your profile.');
    });
}

let topicGeneratorModal;

document.addEventListener('DOMContentLoaded', function() {
    loadUserProfile();
    document.getElementById('saveProfileButton').addEventListener('click', saveUserProfile);
    
    topicGeneratorModal = new bootstrap.Modal(document.getElementById('topicGeneratorModal'));
    document.getElementById('topicGeneratorBtn').addEventListener('click', generateTopics);
});

function generateTopics() {
    showLoading('generatedTopics');
    topicGeneratorModal.show();

    fetch('/generate_topics', {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        const topicsContainer = document.getElementById('generatedTopics');
        topicsContainer.innerHTML = '<h4>Suggested Topics:</h4>';
        const topicList = document.createElement('ul');
        topicList.className = 'list-group';
        
        data.topics.forEach(topic => {
            const listItem = document.createElement('li');
            listItem.className = 'list-group-item list-group-item-action';
            listItem.textContent = topic;
            listItem.onclick = () => selectTopic(topic);
            topicList.appendChild(listItem);
        });
        
        topicsContainer.appendChild(topicList);
    })
    .catch(error => {
        console.error('Error generating topics:', error);
        showError('generatedTopics', 'Failed to generate topics. Please try again.');
    });
}

function selectTopic(topic) {
    document.getElementById('topicInput').value = topic;
    topicGeneratorModal.hide();
    searchSubreddits();
}