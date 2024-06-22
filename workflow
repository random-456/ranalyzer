1. User enters topic or selects a proposed topic
2. Script fetches 10 subreddits via API and analyzes them via another OpenAI API request where it asks it to sort the 10 from the most relevant for that topic descending. It will need to briefly explain the task in the system message. It needs to group them in Most relevant, maybe relevant and maybe not relevant. This will require that a fixed format of the AI models response is followed (e.g. json or whatever) and defined in the system message accordingly. Then print the 10 sorted subreddits in their groups. 
3. User can select one subreddit. Script takes the latest 25 posts (which have at least 1 comment) inside that subreddit and shows them to the user. Also here we need to have a pre-validation of the 25 posts by OpenAI API. Formulate the system prompt which explains that we want to evaluate the list of posts (titles) if they might have potential business models inside them. Group in maybe and maybe not relevant.
4. User can select one post and the analysis is performed as currently.



##########

Now let's improve the UI/UX a bit.
- Use bootstrap for the elements.



##########

We now want to use the full width of the page. And have two boxes next to each other.
On the left we make the choices for the topic, subreddit and post (but now in expandable/collapsible "chapters"). After search term entered, the next chapter opens and then results are being delivered. Then subreddit selected, next chapter opens for posts, the subreddit chapter closes.
On the right we want to see the analysis results after post selection was made.