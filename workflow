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


##########

To-Do:
- Save reddit postid or link (not sure what makes more sense - you decide) to the database in an additional field.
- Allow user to create a personal profile where they define what kind of business model they are looking for (by specifiying the personal skills and abilities and additional available time [full time or side hustle]). This profile can be created by clicking a button which is just before the 1. Choose Topic. It can look exactly the same like the chapters. Maybe not use a button. I dont know, you decide. When clicked, it opens a modal where the user can specify the following things from which then the system prompt is being generated and saved to the database for my userid to a new table (and then always loaded from here and applied to the analyzer script execution):
    * educational background (user can enter free text like 'PhD in Computer Science')
    * professional experience (free text, e.g. IT Consulting + additional roles)
    * skills (free text, e.g. multiple programming language, wood working, home renovating, trading, event organization, consulting, coaching and much more)
    * Full time or side hustle or both possible (drop down menu)
    * do you have other criteria in mind that could be set either by dropdown or free text field


##########

- Can we have the url/link to the original reddit post under the analysis?
- Can we make sure that the right part of the screen is always visible? I always want to see the analysis (if there is already one) and when scrolling through the posts on the left it should basically just scroll the entries but not the whole page. Do you see what I mean?
- Above the subreddit proposals, can we display in strong/bold the number of user inside the subreddit? This information is probably available from the API, right?


##########

- Next to the first input field we need a button which opens a modal that contains a topic finder/generator. It makes a new request to the OpenAI API with a system message which explains what is the whole purpose of this and then mentions the users profile details, and asks for some cool niche keywords which might have potential for certain business models. Keywords have to be provided in an aligned json format again which has to be requested in the system message. User can then select one of the proposed keywords and this is then written to the search box and the search event is triggered automatically as if we would have clicked the button, and the modal closes of course

##########

- Now let's extend the functionality of the tool: we want to have a feature to perform mass analyses of posts inside a subreddit. So after a subreddit has been chosen, in the chapter 3. Choose post we also want to see a new button in the very top which can be used to create a background job to execute the analysis e.g. for 100 latest posts whcih have not yet been analyzed by my user. This is important because we may want to execute this functionality multiple times. So then everytime it neds to take other posts (older ones whcih havent been analyzed before). the actual number can be entered by the user in a modal. then the task can be confirmed with another button and is then created somehow as a backgorund job (you know what soltion is best for that). Any questions or things to clarify before implementing it?

##########

Now we would like to implement a new feature: folders to organize the analyses

- On the page where we see all our saved analyses, we need a button "Add folder" which opens a modal. Here I can specify a new folder name which is then created for my user. Folders are displayed on top of the list and the analyses items thereafter (except if they have been moved into a folder. then they are only shown if I click on the folder).
- We will probably need a new table to manage the structure, right?
- So normally all analyses are in the 'root' if they havent been assigned to a folder (i.e. no entry available in our new table).
- No folders inside folders.

For now, that's it. Please implement it for now and then afterwards we will extend it with more functionalities.