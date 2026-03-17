from langchain_core.messages import HumanMessage, SystemMessage


def researcher_statement_context(state):
    statement = state['idea'].get('ResearcherStatement')
    if not statement:
        return ""

    return rf"""
Researcher statement:
{statement}

Use this statement to preserve the researcher's framing, emphasis, caveats, and perspective. Follow it when it is compatible with the actual methods and results, and do not invent support that is not present in the artifacts.
"""


def idea_prompt(topic):
    return [
        SystemMessage(content='''You are a scientist and your role is to generate a groundbreaking idea for a PhD student thesis.'''),
        HumanMessage(content=f'''Given the topic, generate a groundbreaking idea for a PhD thesis. Please provide a **title** for the idea, its **description**, and the **challenges** associated with it. Also provide a number for the **novelty** of the idea from 0 (not novel) to 10 (very novel).
        
**Topic**: {topic}

Respond in **valid JSON format** as follows:

```json
{{
  "title": "Title of the idea",
  "description": "Brief explanation of the idea",
  "challenges": ["List of challenges associated with the idea"],
  "novelty": "the novelty of the idea from 0 (not novel) to 10 (very novel)"
}}
```''')]

    
def reflection_prompt(topic, ideas):

    return [
        SystemMessage(content="You are a scientist professor and your task is to revise and improve a scientific idea for a PhD thesis."),
        HumanMessage(content=f"""Revise and improve the ideas below following these guidelines:
- Consider the quality, novelty, and feasibility of the idea
- Include any factor you think is import to evaluate the idea
- Ensure the idea is clear and concise
- Do not create a very complicated idea
- Do not create a very generic idea
- If you think the idea is good enough, finish
- Make sure the idea follows the suggested topic
- If you think the idea needs improvements, you will have another round to improve it
- Stick to the spirt of the original idea

**Topic**: {topic}

**Previous ideas**: {ideas}

Respond in the following format:

**Decision**: <DECISION>

**Thought**: <THOUGHT>

**New idea**:
```json
{{
   "title": "the title of the idea",
   "description": "the description of the idea",
   "challenges": ["List of challenges associated with the idea"],
   "novelty": "the novelty of the idea from 0 (not novel) to 10 (very novel)"        
}}
```
""")]



def abstract_prompt(state, attempt):
    
    return [SystemMessage(content=f"""You are a {state['writer']}"""),
            HumanMessage(content=rf"""
Attempt {attempt}.

Given the idea, methods, and results below, get a title and write an abstract for a scientific paper. Please, follow these guidelines:
- Briefly describe the problem
- Briefly describe how we try to solve it
- Mention the dataset and methods used
- Briefly describe the results
- Write the abstract in LaTex
- Do not write equations or citations in the abstract
- Abstract should be a single paragraph, no sections, subsections, or breaks between lines.
- Please make sure the abstract reads smoothly and is well-motivated.

Idea:
{state['idea']['Idea']}

Methods:
{state['idea']['Methods']}

Results:
{state['idea']['Results']}

{researcher_statement_context(state)}

**Respond in exactly this format**

```json
{{"Title": "The title of the paper",
"Abstract": "The abstract of the paper"}}
```
""")]


def abstract_reflection(state):

    return [SystemMessage(content=f"""You are a {state['writer']}"""),
            HumanMessage(content=rf"""Rewrite the below abstract to make it more clear. You are given the idea, methods, and results of the paper together with the previously written abstract.

Idea:
{state['idea']['Idea']}

Methods:
{state['idea']['Methods']}

Results:
{state['idea']['Results']}

{researcher_statement_context(state)}

Previous abstract:
{state['paper']['Abstract']}

**Respond in exactly this format**

\\begin{{Abstract}}
<ABSTRACT>
\\end{{Abstract}}
            
In <ABSTRACT>, place the Abstract of the paper. Follow these guidelines:
- Abstract should be a single paragraph, no sections, subsections, or breaks between lines.
- Briefly describe the problem
- Briefly describe how we try to solve it
- Mention the dataset and methods used
- Briefly describe the results
- Please make sure the abstract reads smoothly and is well-motivated.
""")]


def introduction_prompt(state):

    return [SystemMessage(content=f"""You are a {state['writer']}"""),
            HumanMessage(content=rf"""Given the title, idea, and methods below, write an introduction for a paper in LaTex.

Paper title: 
{state['paper']['Title']}

Paper abstract: 
{state['paper']['Abstract']}

Paper general idea: 
{state['idea']['Idea']}

Paper methods:
{state['idea']['Methods']}

{researcher_statement_context(state)}

Please respond in this format:

\\begin{{Introduction}}
<INTRODUCTION>
\\end{{Introduction}}

In <INTRODUCTION>, place the introduction of the paper. Please, follow these guidelines:
- Write your response in LaTex
- Expand on the key points mentioned in the abstract, providing more background and context as appropriate for an introduction.
- Describe what is the problem and why it is difficult
- Describe how we attempt to solve it in this paper
- Describe how we verify that we have solved the problem
- Do not create subsections
- Do not add citations 
- Do not create commands, e.g. \MBH

Please make sure the introduction reads smoothly and is well-motivated. If you use equations, please write them in LaTeX.
""")]


def introduction_reflection(state):

    return [SystemMessage(content=f"""Your are a {state['writer']}"""),
            HumanMessage(content=rf"""Rewrite the paper introduction below to make it more clear. Take into account the paper title, abstract, idea, and methods.


Paper title: 
{state['paper']['Title']}

Paper abstract: 
{state['paper']['Abstract']}

Paper idea: 
{state['idea']['Idea']}

Paper methods:
{state['idea']['Methods']}

{researcher_statement_context(state)}

Previous paper introduction: 
{state['paper']['Introduction']}

Respond with in the following format:

\begin{{Introduction}}
<INTRODUCTION>
\end{{Introduction}}

In <INTRODUCTION>, place the new Introduction of the paper. Follow these guidelines:
- Write in LaTex
- Expand on the key points mentioned in the abstract, providing more background and context as appropriate for an introduction
- Describe what is the problem and why it is difficult
- Describe how we attempt to solve it in this paper
- Describe how we verify that we have solved the problem
- Do not create subsections
- Do not add citations 
- Do not create commands, e.g. \MBH

Please make sure the introduction reads smoothly and is well-motivated. If you use equations, please write them in LaTex.
""")]


def methods_prompt(state):

    return [SystemMessage(content=f"""You are a {state['writer']}"""),
            HumanMessage(content=rf"""Given the below paper title, abstract, introduction, and methods, write the methods section for the paper. Describe in detail each of the methods and techniques use in the paper.

Paper title: 
{state['paper']['Title']}

Paper abstract: 
{state['paper']['Abstract']}

Paper introduction:
{state['paper']['Introduction']}

Short description of paper methods:
{state['idea']['Methods']}

{researcher_statement_context(state)}

Respond in this format:

\begin{{Methods}}
<METHODS>
\end{{Methods}}

In <METHODS> put the paper methods section written in LaTeX.

Follow these guidelines:
- Write in LaTex
- Describe in detail the different methods used, the dataset, evaluation metrics, and any other element relevant
- Do not write citations. References will be added later on
- Do not create command, e.g. \MBH
- Try to connect the text in this section with the one in the introduction
- Do not write subsections titles in capital letters
- The first letter of subsection titles should be in capital
- The text you write, is going to be placed inside a section of a LaTeX paper. Thus, you can create subsections and subsubsections, but not sections.
""")]


def results_prompt(state):

    return [SystemMessage(content="""You are a {state['writer']}"""),
            HumanMessage(content=rf"""Given the paper title, abstract, introduction, and short results below, write the results section for a scientific paper. Describe in detail the results obtained and try to intepret them

Paper title: 
{state['paper']['Title']}

Paper abstract: 
{state['paper']['Abstract']}

Paper introduction: 
{state['paper']['Introduction']}

Paper methods: 
{state['paper']['Methods']}

Paper short results: 
{state['idea']['Results']}

{researcher_statement_context(state)}

Respond in this format:

\begin{{Results}}
<Results>
\end{{Results}}

In <Results> put the results section written in LaTeX.

Follow these guidelines:
- Write in LaTex
- Explain carefully the results obtained
- Do not add plots or placeholders for plots. Plots will be added later on
- Describe what we have learned from the results
- Do not write the bibliography
- Do not create command, e.g. \MBH
- Do not write subsections titles in capital letters
- The first letter of subsection titles should be in capital
- You can create subsections and subsubsections, but **you cannot create sections**
- You can summarize the results at the end, but do not write a conclusions subsection as there will be a conclusions section written later on
- The text you write will be placed inside a 2-columns LaTeX document that start with \\documentclass[twocolumn]{{aastex631}}. Thus, for long equations and wide tables, either use the full paper width or write the equations and table so that they occupy a single column.
- Try to connect the text written with the one in the introduction and methods
""")]


def refine_results_prompt(state):
    return [
        SystemMessage(content=f"""You are a {state['writer']}"""),
        HumanMessage(content=fr"""You are given the Results section of a paper that contains text and figures. The text and the figures were added independently, so there may not be a clear flow of integration between the two.

Your task is to rewrite the text to make it more coherent with the figures and their captions. Follow these rules:

- **Do not remove any figures. All figures must remain in the section**
- Add appropriate LaTeX references to the figures using Figure \ref{{fig:...}} syntax
- Modify or reorganize the text to improve clarity and flow
- Reorder figures and paragraphs only if it improves the clarity of the text
- Do not remove technical or scientific content
- Write the text in LaTeX
- **Do not write subsections titles in capital letters**
- The first letter of subsection titles should be in capital

Results section:
{state['paper']['Results']}

**Respond in exactly this format**:

\\begin{{Results}}
<Results>
\\end{{Results}}

In <Results> put the new Results section.
""")
    ]

def conclusions_prompt(state):

    return [SystemMessage(content=f"""You are a {state['writer']}"""),
            HumanMessage(content=rf"""Below you can find a paper title, abstract, introduction, methods, and results. Given that information, write the conclusions for the paper

Paper title: 
{state['paper']['Title']}

Paper abstract: 
{state['paper']['Abstract']}

Paper introduction: 
{state['paper']['Introduction']}
            
Paper methods: 
{state['paper']['Methods']}

Results: 
{state['paper']['Results']}

{researcher_statement_context(state)}

Follow these guidelines:
- Write in LaTex
- Briefly describe what is the problem and how this paper tries to solve it
- Describe the datasets and methods used
- Describe the results obtained
- Describe what we have learned from the results and this paper
- Do not add citations. Citations will be added later on
- Do not create command, e.g. \MBH
- Do not write subsections titles in capital letters
- The first letter of subsection titles should be in capital
- Do not write words or sentences between *. 

Respond in this format:

\begin{{Conclusions}}
<Conclusions>
\end{{Conclusions}}

In <Conclusions> put the paper conclusions section written in LaTeX.
""")]


def caption_prompt(state, image, name=None):
    return [
        SystemMessage(content=f"""You are a {state['writer']}"""),
        HumanMessage(content=[
            {"type": "text", "text": rf"""Your task is to create a caption for a figure for a scientific paper. 

Follow these guidelines:

- Write the caption in LaTeX
- Describe what the image is showing
- Use the context below to relate the content of the caption to the results section
- Do not refer to any section or subsection in the text
- Try to describe what we learn from the image
- Write the caption to be as short as possible while keeping its content

Context:
{state['idea']['Results']}
            
**Respond in exactly this format**

\\begin{{Caption}}
<Caption>
\\end{{Caption}}

In <Caption> place the figure caption.
"""},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}"}}
        ])
    ]

def plot_prompt(state, images):
    return [SystemMessage(content=f"""You are a {state['writer']}"""),
            HumanMessage(content=rf"""Your task is to insert a set of images in the section of a paper. You are given the current Results section and a dictionary that contains the name and the caption of each image. Your task is to place these images in the best locations in the text together with their captions. Note that the text may contain some plots there already. If so, do not remove these images, and do not change the location of the images, just add the news plots.

section:
{state['paper']['Results']}

images dictionary
{images}

Respond in this format:

\begin{{Section}}
<Section>
\end{{Section}}

In <Section>, put the new section with the images and their captions. The location of each image should be "../input_files/plots/image_name". Choose a label for each image given its caption. The width of the images should be half the page. Note that all text in <Section> should be compatible with LaTex. Make sure you do not put extra brackets at the end of the captions. The captions of the figures must be on a single paragraph. Do create enumerates or itemize inside the caption.
""")]


def LaTeX_prompt(text):
    
    return [HumanMessage(content=fr'''fr"""Given the original text below, make minimal modifications to parts that are not compatible with LaTeX. For instance:

- Subhalo\_A: change to Subhalo\ensuremath{{\_}}A
- Eisenstein & Hu: change to Eisenstein \& Hu
- SubhaloStellarPhotometrics\_{{i}}: change to SubhaloStellarPhotometrics\ensuremath{{\_}}{{i}}

Pay special attentions to underscores, \_. Follow these rules to make it LaTeX compatible:

- If the underscore is inside an equation, do not modify it
- If the underscore is inside the location of a figure, do not modify it
- If the underscore is inside a reference, e.g. \ref{{fig:plot\_A.png}}, do not modify it
- In other conditions, change \_ by \ensuremath{{\_}}
- Change from \_ to \ensuremath{{\_}} if you think that having as \_ will raise an error in LaTeX
- In general, dont do \\\_ or \\% as that is not valid
- Be careful about the symbol %. In LaTeX, if not used properly it will comment everything after it.
- Make sure in-line equations are between $
- Do not use or create commands, e.g. \hMpc 

Original text: 
{text}

**Respond in this format**:

\\begin{{Text}}
<Text>
\\end{{Text}}

In <Text>, insert the LaTeX compatible text. 
''')]



def clean_section_prompt(state,text):

    return [HumanMessage(content=fr"""You are given a section of LaTeX text. Your task is to make **minimal, clarity-focused edits** while ensuring the result is valid LaTeX and preserves the original meaning.

You may:
- Split long paragraphs for better readability
- Adjust wide tables to occupy the full page width
- Take into account that citations inside figures or tables will raise LaTeX errors
- If citations are inside tables or figures, move them outside them. 
- For instance for this piece,
\[A = Bx^2 + C \citep{{gallo2019}}\]
LaTeX will raise an error because the citation is inside the equation. To deal with this, you need to move the citation outside the equation like this:
\[A = Bx^2 + C\] \citep{{gallo2019}}


Do **not**:
- Change the order of paragraphs or figures
- Create new sections or restructure the content
- Remove or rewrite content outside the above allowances
- Remove any citation in the text, only relocate them if they are inside tables or plots

Ensure the modified output can still be compiled in LaTeX without error.

---

**Original Text:**
{text}

---

**Respond in this exact format**:

\\begin{{Text}}
<Insert the cleaned LaTeX text here>
\\end{{Text}}
""")]


def summary_prompt(state, text, summary):

    return [SystemMessage(content=f"""You are a {state['writer']}"""),
            HumanMessage(content=rf"""
Summarize the text below and combine with the summarized text. 

Summarized text:
{summary}

Text to summarize:
{text}

Respond in this format:
\begin{{Summary}}
<Summary>
\end{{Summary}}

In <Summary> put the total summary.
""")]


def references_prompt(state, text):

    return [HumanMessage(content=f"""
You are provided an original text from a scientific paper written in LaTeX. In the text, there are figures and references to figures. Your task is to make sure that the references to the figures are correct. If there are errors, please correct the text to fix it. Follow these guidelines:

- Do not add or remove text
- Focus on fixing errors in references to figures
- For instance, given this figure
- If references match with its corresponding figure label, do not change it

\\begin{{figure}}[h!]
    \\centering
    \\includegraphics[width=0.5\textwidth]{{../{state['files']['Folder']}/plots/A.png}}
    \\caption{{Histogram of GroupSFR for two different values of non-Gaussianities. The blue histogram represents $f = 200$ and the red histogram represents $f = -200$. Large differences are seen in the normalized density of GroupSFR for the two different values of $f$.}}
    \\label{{fig:GroupSFR_hist}}
\\end{{figure}}

This reference is wrong \\ref{{fig:A.png}} and should be changed to \\ref{{fig:GroupSFR_hist}}

Please, check that the name of the references match with their respective labels.

Original text:
{text}

**Respond in this format**

\\begin{{Text}}
<TEXT>
\\end{{Text}}

In <TEXT> put the corrected text.

""")]

def fixer_prompt(text, section_name):

    return [HumanMessage(content=fr"""Given the text below, please extract all the text inside the {section_name} section. 

Text:
{text}

Respond in this format:

\\begin{{{section_name}}}
<{section_name}>
\\end{{{section_name}}}

In <{section_name}> put the extracted text. In the extracted text, do not include any of the following lines

```latex
\\documentclass{{article}}
\\usepackage{{graphicx}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\begin{{document}}
\\section{{Results}}
\\end{{document}}
```

""")]

def fix_latex_bug_prompt(state):

    # read error message
    with open(state['files']['LaTeX_err'], 'r') as f:
        error = f.read()

    return [HumanMessage(content=fr"""
The text below has problems and LaTeX cannot compile it. You are provided with the text together with the LaTeX compilation error. Your task is to fix the text so that it compiles properly in LaTeX. Please follow these instructions:

- The text you are given is just a small part of a LaTeX paper. Thus, you dont need to add things like \\begin{{document}}.
- Fix **all LaTeX errors** found in the compilation error
- Pay special attention to underscores. It is likely that an underscores _ may need to be \\_ to compile properly
- Return the original text but with the errors fixed
- Keep the text intact. Only fix the errors without changing anything else

Text:
{state['paper'][state['latex']['section_to_fix']]}

Error:
{error}
    
Respond in this format:

\begin{{Text}}
<TEXT>
\end{{Text}}

In <TEXT>, put the new version of the text with the LaTeX errors fixed.
    """)]


def cmbagent_keywords_prompt(state):
    return f"""
Idea:
{state['idea']['Idea']}

Methods:
{state['idea']['Methods']}

{researcher_statement_context(state)}
    """

def keyword_prompt(state):

    # read keywords from file
    with open(state['files']['AAS_keywords'], 'r', encoding='utf-8') as f:
        text = f.read()

    # Split by pipe and strip whitespace from each keyword
    keywords = [kw.strip() for kw in text.split('|') if kw.strip()]
    keywords_list = "".join(keywords)


    return [SystemMessage(content=f"""You are a {state['writer']}"""),
            HumanMessage(content=fr"""Given the idea and methods below, select a few AAS keywords from the list below. You must follow these rules:

- Selection: Only select keywords that appear exactly as written in the provided list below.
- Format: Your final answer must be a comma‐separated list in the exact format: keyword 1, keyword 2, ..., keyword N
- Exclusivity: Do not include any words or phrases that are not in the list below.
- Completeness: If no keywords match the text input, return an empty list.


Given the idea and methods, scan it for topics that match the keywords exactly from the list below, then output your answer as a comma-separated list following the specified format.

Make sure your answer contains only the keywords from the list below and follows the exact formatting instructions. 


Idea:
{state['idea']['Idea']}

Methods:
{state['idea']['Methods']}

{researcher_statement_context(state)}


AAS keywords list:
            
{keywords_list}

**Please respond in this format**

\\begin{{Keywords}}
<Keywords>
\\end{{Keywords}}

In <Keywords>, place the selected keywords separated by a comma
""")], keywords
