from langchain_core.runnables import RunnableConfig
from .parameters import GraphState
from .prompts import novelty_prompt, summary_literature_prompt
from ..paper_agents.tools import extract_latex_block, LLM_call_stream, json_parser3
import time, sys
import requests
from tqdm import tqdm


    
# This node determines if an idea is novel or not. It may also ask for literature search
def novelty_decider(state: GraphState, config: RunnableConfig):
    """
    The goal of this function is to determine if an idea is novel or not. The function is given access to semantic scholar to find papers related to the project idea.
    """
    
    print(f"\nAddressing idea novelty: round {state['literature']['iteration']}")

    # check if idea is novel or not
    PROMPT = novelty_prompt(state)

    # Try for three times in case it fails 
    for _ in tqdm(range(5), desc="Analyzing novelty", unit="try"):
        
        state, result = LLM_call_stream(PROMPT, state)
        try:
            result    = json_parser3(result)
            reason    = result["Reason"]
            decision  = result["Decision"]
            query     = result["Query"]
            messages = f"{state['literature']['messages']}\nIteration {state['literature']['iteration']}\ndecision:{decision}\nreason:{reason}\n"
            iteration = state['literature']['iteration'] + 1
            break
        except Exception:
            time.sleep(2)

    else:
        raise Exception('Failed to extract json after 5 attempts')
        
    # get the reason for the decision
    if 'not novel' in decision.lower():
        print('Decision made: not novel')
        return {"literature": {**state['literature'], "reason": reason, "messages": messages,
                               "decision": decision, "query": query, "iteration": iteration,
                               'next_agent': "literature_summary"}}
    
    elif 'novel' in decision.lower() or iteration>=state['literature']['max_iterations']:
        decision = 'novel'
        print('Decision made: novel')
        return {"literature": {**state['literature'], "reason": reason, "messages": messages,
                               "decision": decision, "query": query, "iteration": iteration,
                               'next_agent': "literature_summary"}}

    else:
        # Get the value of the "Query" field
        print('Decision made: query')
        print(f'Query: {query}')
        return {"literature": {**state['literature'], "reason": reason, "messages": messages,
                               "decision": decision, "query": query, "iteration": iteration,
                               'next_agent': "semantic_scholar"}}
    

# This node will use semantic scholar to search for papers similar
# to the ones in the query
def semantic_scholar(state: GraphState, config: RunnableConfig):
    """
    This agent will search for papers given the search query and return the list of found ones
    """
    
    # search papers given the query
    results = SSAPI(state['literature']['query'], state['keys'], limit=20)

    total_papers = results.get("total", []) #total number of relevant papers found
    papers       = results.get("data",  []) #the actual data of the retrieved papers

    # A list with the idx, title, abstract, and url of the found papers. To be passed to the other agent
    papers_str = []
    papers_analyzed = 0
    if papers:
        print(f"Found {total_papers} potentially relevant papers")

        # do a loop over the papers
        for idx, paper in enumerate(papers, start=0):

            # get the different fields of the paper
            authors = ", ".join([author.get("name", "Unknown") for author in paper.get("authors", [])])
            title      = paper.get("title",         None)
            year       = paper.get("year",          None)
            abstract   = paper.get("abstract",      None)
            url        = paper.get("url",           None)
            ID         = paper.get("paperId",       None)
            externalID = paper.get("externalIds",   None)
            pdf        = paper.get("openAccessPdf", None)

            if abstract is None:
                continue
            else:
                papers_analyzed += 1
            
            # string with paper information
            paper_str = f"""{papers_analyzed+state['literature']['num_papers']}. {title} ({year})\nAuthors: {authors}\nAbstract: {abstract}\nURL: {url}"""

            # extract arXiv link, if any
            arXiv_pdf = None
            arXiv_pdf2 = None
            if externalID:
                arXiv = externalID.get("ArXiv", None)
                if arXiv:
                    arXiv_pdf  = f"https://arxiv.org/pdf/{arXiv}"
                    arXiv_pdf2 = f"http://arxiv.org/pdf/{arXiv}" #sometimes the pdf url has https and sometimes http. Use both to avoid duplication.
                    paper_str = f"{paper_str}\narXiv link: {arXiv_pdf}"

            # extract pdf link, if any
            if pdf:
                pdf = pdf.get('url', None)
                if pdf and (arXiv_pdf is None or (pdf!=arXiv_pdf and pdf!=arXiv_pdf2)):
                    paper_str = f"{paper_str}\npdf: {pdf}"
            
            # put these papers in the literature.log
            paper_str = f"{paper_str}\n\n"
            with open(f"{state['files']['literature_log']}", 'a') as f:
                f.write(paper_str)

            # put papers into the papers_processed.log file
            with open(f"{state['files']['papers']}", 'a') as f:
                f.write(paper_str)

            paper_str = papers_str.append(f"""{idx+state['literature']['num_papers']}. {title} \nAbstract: {abstract}\nURL: {url}\n""")
    else:
        papers_str.append("No papers found with the query.\n")

    total_papers_found = state['literature']['num_papers'] + papers_analyzed
    print('Total papers analyzed', total_papers_found)
    
    return {"literature": {**state['literature'], 'papers': papers_str, "num_papers":total_papers_found}}


def SSAPI(query, keys, limit=10) -> list:
    """
    Search for papers similar to the given query using Semantic Scholar API.

    Args:
        query (str): The search query (e.g., keywords or paper title).
        keys (dict): a python dictionary containing the session keys, including the semantic scholar one
        limit (int): Number of papers to retrieve (default is 10).

    Returns:
        list: A list of dictionaries containing paper details.
    """

    # Base URL for Semantic Scholar API
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    params = {"query": query,
              "limit": limit,
              "fields": "title,authors,year,abstract,url,paperId,externalIds,openAccessPdf"}

    # For each query, call Semantic Scholar a maximum of 200 times.
    # When no Semantic Scholar key is present, the system may return an error
    for _ in tqdm(range(200), desc="Calling Semantic Scholar", unit="try"):

        # Conditionally include headers if API_KEY is available
        if keys.SEMANTIC_SCHOLAR:
            response = requests.get(BASE_URL,
                                    headers={"x-api-key": keys.SEMANTIC_SCHOLAR},
                                    params=params)
        else:
            response = requests.get(BASE_URL, params=params)
            
        if response.status_code==200:
            return response.json()
        else:
            time.sleep(0.5) #wait for 1/2 second before retrying
        
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return []


    
def literature_summary(state: GraphState, config: RunnableConfig):
    """
    This agent will take all messages from previous iterations and write a summary of the findings
    """

    # generate the summary
    PROMPT = summary_literature_prompt(state)    
    state, result = LLM_call_stream(PROMPT, state)
    text = extract_latex_block(state, result, "SUMMARY")

    # write summary to file
    with open(f"{state['files']['literature']}", 'w') as f:
        f.write(f"Idea {state['literature']['decision']}\n\n")
        f.write(text)

    # print out the summary
    print(text)

    print(f"done {state['tokens']['ti']} {state['tokens']['to']}")
