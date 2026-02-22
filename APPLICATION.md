This is a new application like tinyclaw (repo here https://github.com/jlia0/tinyclaw/tree/main ) that:
- Is a system to run multiple agents in the background
- Uses Ollama as a backend but allows optional use of Gemini via an API key that we can specify later.
- The agent should lean to balance it's usage between the two, using Gemini for High Value complex problems, and ollama for basic problems. There will need to be a decison point and this should prefer Ollama where costs are low.
- It will be run in a docker container, and eventually run inside a small kubernetes cluster I run at home
- Use Python for the language
- Use UV for the package manager
- Liek Tinyclaw, I like the idea of SOUL.md, I want agents to learn from each other and from the user over time. I want them to be able to be the best they can be and to grow and improve over time.
- We can give the agents some tools that are available locally at first, like searxng for searching the web, It is available at https://searxng.crobasaurusrex.ryanbeales.com/
- Over time I'm going to ask the agents themselves to create new tools that will be available to them. They need to be able to create and learn how to use these tools and make them available to applicable agents, perhaps not every agent will have access to every tool.
- The main interface will be a web interface that allows users to interact with the agents via a chat interface. It will be like an IRC channel where every agent is available in the channel and the user can chat directly with each of them if required.
- At first there will be a single agent that will be able to create new agents.
- We will want to add a judge agent that will have the ability to judge the output quality from other agents, and encourage them to improve. If they don't improve they can be fired and a new one hired to take it's place. We want to look for a better performing agent if the judge deems it necessary.
- The agents will be able to defer tasks, so scheduling is important. Eg: if an agent is required to check on something every hour it needs the capability to do so. If the user asks an agent to perform an action by a certain date, it should be able to schedule it to do so.
- If the agents require the users attention they will do so buy tagging the user name in the chat interface.
- It's important that the chat history is preserved so that if the user is not viewing the UI at the time the agents can continue to work, and when the user returns to the UI they can see the full conversation history.
- There are agent skills in this repository that you will build this app with, if you deem them important for the agents to use then we need to make these instructions available to the agents in this new app also.

The end goal, is that over time will have a collection of expert agents that are able to work together and tackle any problem given to them by the user.