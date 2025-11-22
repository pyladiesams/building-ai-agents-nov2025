> origianl workshop at https://github.com/Cheukting/BuildingAIAgent

# Building an AI agent

In this workshop, we will first study the relationship between an AI Agent and an AI model. Then, by some hands on exercises, we will learn how to choose the right model for building your own AI Agent; and how to build an AI Agent from scratch.

This workshop is designed for participants to be creative and come up with their own unique AI agent ideas. We will only provide the basic knowledge and techniques needed to build an AI agent and guidance for problem solving.

By building an AI Agent and comparing AI models, we will learn more about how AI Agent works and all thing we need to know when considering building an AI Agent for commercial use.

## Prerequisites

This workshop is for those who are confident in coding in Python and have a basic understanding of software development. Knowledge of AI models and AI Agents is not required.

## AI model and AI Agents

###  What's the difference?

When we talk about AI model, we usually mean a machine learning model that can be used to perform a specific task. For example, a model that can be used to perform image classification or text generation. When we talk about AI Agent, we usually mean a software that can interact with humans and use AI models to solve problems. For example, according to the user's prompt, count how many objects fit the description are in a certain image.

### Why do we need AI agent?

As a rough analogy, AI models are to AI agents what engines are to cars. Without engines, there would be no cars. Many people know how to drive a car and get to where they want to be, but they don't know how to make  engines works together with other mechanical parts to make a car, thus making engines useless. Creating an AI agent is like the mechanic building a car, creating a tool that can be used by users who many not have the technical know how of the AI model to get the job done.

AI agent can also be an end-to-end solution to complete a multi-step task. It can evaluate the intermediate results and make adjustments and repeat the process until the task and requirements are satisfied.

## How to choose an AI model

### Which AI model for what tasks?

First thing about choosing what AI model to use is depending on what task you want to complete. For example, if you want to build an AI agent that can perform coding tasks, you may need to choose an LLM that understand coding problems and would be able to provide an action plan of how to complete the tasks. It may also need to be able to write code to some of your files.

Hugging Face Hub provides a lot of open sources models that you can use and fine tune to suit your purpose. The most interesting models would be the LLMs. LLMs (Large Language Models) are commonly a key components in AI agents as they can understand the users prompt and requirements which are natural languages.

### Open source and proprietary models

One limitation of open source models is it may need the proper computing hardware and infrastructure to run the AI models. Although the modern computers these days have multiple cores and are quite powerful, it may still be lagging in running a larger model. Setting a remote AI model server will require technical know-how and also require extra cost. Open sources models may also have limited licenses when used commercially. Make sure to always check the usage licenses when downloading an open source model.

## Exercise 1 - Trying different LLMs on Hugging Face

In this exercise, we will explore some open source LLMs on Hugging Face. We will focus on using models that are available in llamafile format. To learn more about llamafile and how to use it, please refer to the [Exercise_1/how_to_llamafile.md](Exercise_1/how_to_llamafile.md). Get 1 or 2 model llamafiles and play around with it and try them out. Pick one to be used in the following exercises.

A few things to consider when choosing a LLM:

- the size of the model
- does the LLM understand enough about the task
- response time after a prompt is given
- the quality of the response

Good things to try for building our AI agent in the later exercises:

- parsing a prompt into json with required information extracted
- asking the LLM to provide answers in json format

If the LLM cannot provide the above in json format, we may run into troubles later when building our AI agent.

## Designing an AI agent

### What task to complete?

Now we have a LLM running locally, we can think about how to create our AI agent. First of all, we need to give a purpose of the AI agent. While a general purpose AI agent is possible, it will be more complicated to build and require more resources.

Here are some ideas for you to choose, feel free to come up with something similar:
- AI travel agent that can make recommendation on itineraries and bring you to the booking websites
- AI book recommendation agent that can make book recommendation and bring you to purchase with both printed book and audio book version if available.

### What tools do we need?

After deciding of what AI agent to build, the next step will be to think about the steps the agent will potentially take and what tools we can provide for the agent. Tools are resources the AI agent can use to help completing the tasks given by the users. For example, maybe there will be a tool scan all the files in a directory in the file system, a tool to add a file, a tool to edit a file and a tool to delete a file.

Tools can be provided internally in the agent or it can be added with MCP servers.

### Using an MCP server

MCP (Model Context Protocol) servers are a way to provide extra tools to the agent on top of the built-in ones. Since the MCP standardize the connect between an AI agent and an external application, third party tools can be developed by anyone to extend the capability of the AI agent. The MCP server can be a standalone server or a service that can be used by multiple agents.

In this workshop we will not use MCP servers, but you can learn more about them in the [MCP documentation](https://github.com/modelcontextprotocol/python-sdk).

### User interfaces

The last piece of the puzzle is to have a user interfaces so it is easy for the user to interact with the agent. The minimum requirement for the user interface is to have an interface for the user to input prompts and have a way to provide feedback from the agent.

For example, we can accept a prompt from the user with standard io in the terminal, then we will provide a recommended travel itinerary for the user, the user can then add follow up prompts to refine their itinerary. When the user is happy, the agent will open the booking sites in new browser windows for the user to complete the booking.

## Exercise 2.1 - Design an AI agent

In this exercise, we will start by writing down our AI agent design. You can use any tools or event pen and papers for this exercise. Try follow the steps below.

1) Think of what kind of AI agent you would like to build. To make it simple, narrow the scope by picking a specific task the AI agent is designed for. Here are a few ideas:

   - A song/ book recommendation agent that can recommend songs/ books based on the user's preference
   - A travel agent that can recommend itineraries based on the user's preference
   - A file management agent that can manage files in a directory
   - A scheduling agent that can schedule daily tasks based on the user's preference
    
   You can also come up with your own. Bonus point if this agent can help you solving real life problems.

2) Next, think about what tools you would like to provide to the agent. Tools can be subprocesses, APIs, or even a web server. For APIs, here are a list of [public APIs](https://github.com/public-apis/public-apis) that you may find useful. When we build the agent we will have to define those and provide information about them to the LLM.

3) After that, think about what user interface you would like to provide to the agent. The simpliest would be a command line interface. However, command line interface is text based and limited in what it can present. In other words, if you would like to present multi-media to users, we can use a web interface to provide a better user experience instead.

## Exercise 2.2 - Build an AI agent

In this exercise, we will build an AI agent using the tools and user interface we designed in the previous exercise. Before we build it our own, first, look at the code in the [Exercise_2/agent.py](../solutions/Exercise_3/benchmark.py) file and learn how to do it. Here are the highlights:

1) LLM backend (llamafile) client
    - In the example we used http requests with the backend, alternatively you can also use [OpenAI's python client](https://pypi.org/project/openai/) as llamafile are [compatable with OpenAI's API](https://github.com/Mozilla-Ocho/llamafile?tab=readme-ov-file#json-api-quickstart).
    - We will provide system messages (see [line 193]) to the LLM to provide instructions. Notice that we have defined the json format that we required. In this agent we did not need to tell LLM what tools we have available as the role fo the LLM here is to parse the user's prompt into search parameters. If you require the LLM to provide decision or action plans based on the tools then information about the tools should be provided to the LLM here as well.

2) Tools: External data sources
    - In this agent we have 3 tools available for searching the movie recommendations, getting the movie summaries and trailers.

This agent also have a web server that can be used to provide the user interface. We build it using fastapi and uvicorn. See the [Exercise_2/web_server.py](Exercise_2/web_server.py) file for more details.

Now try to build your own agent. Start small first then add functionality one by one. You can use the code in the agent.py file as a reference.

## Improve the performance

### Testing and benchmarking your agent

Just like any other software, we need to test and benchmark the performance of our agent. Treat it like running a machine learning experiment and measure the performance of the model, which is our agent.

The most efficient way to test the performance of our agent is to run it against a significant number of test cases automatically with another Python script, record the results and analyse them. We will perform the same after tweaking with the agent so we can compare the performance of our agent before and after we make changes.

### Performance improvement plans

There are things we can try to implement to improve the performance of our agent. Which way works depends on the problem and the agent. Here are some ideas:

- Filter out irrelevant information in the prompt
- Provide clearer instruction in the system prompts
- Provide different/ more tools to the agent and LLM
- Do we need more information from the user? If so how to ask the user for more information
- Use a different LLM that is more capable

Focus on what tasks you want the agent to be good at. A good strategy is to start making the agent good at a small ranges of tasks first before trying to generalize it.

## Exercise 3.1 - Benchmark your agent

In [Exercise_3/e2e_test.py](../solutions/Exercise_3/e2e_test.py), we perform end-to-end tests, and in [Exercise_3/benchmark.py](../solutions/Exercise_3/benchmark.py), we have provided a simple benchmarking script that is use to test the performance of the example agent in Exercise_2. See [Exercise_3/test_and_benchmark.md](../solutions/Exercise_3/test_and_benchmark.md) for more details.

After that, try adding more test cases in [Exercise_3/test_cases.json](../solutions/Exercise_3/test_cases.json) and run the testing and benchmarking script. Check the Exercise_3/logs folder to see the results.

Are the results good enough? If not, what can we do to improve the performance? We will look at that in the next section. Now think about implementing similar testing and benchmarking scripts for your own agent.

## Exercise 3.2 - Improve the performance of your agent

Try implementing the improvements we discussed in the previous section to see if that improves the performance of your agent. You may want to experiment with the example agent in Exercise_2, before you start with your own agent. Discuss with others to see if you can come up with a good strategy.

---

## Support this workshop

This workshop is created by Cheuk and is open source for everyone to use (under MIT license). Please consider sponsoring Cheuk's work via [GitHub Sponsor](https://github.com/sponsors/Cheukting).
