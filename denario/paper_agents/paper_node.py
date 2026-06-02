from langchain_core.runnables import RunnableConfig
import random
import base64
import time
from pathlib import Path
from tqdm import tqdm
import asyncio
from functools import partial
import fitz  # PyMuPDF
import cmbagent

from .parameters import GraphState
from .prompts import abstract_prompt, abstract_reflection, caption_prompt, clean_section_prompt, conclusions_prompt, introduction_prompt, introduction_reflection, keyword_prompt, methods_prompt, plot_prompt, references_prompt, refine_results_prompt, results_prompt, cmbagent_keywords_prompt
from .tools import json_parser3, LaTeX_checker, clean_section, extract_latex_block, LLM_call, temp_file, check_images_in_text
from .literature import process_tex_file_with_references
from .latex import compile_latex, save_paper, save_bib, process_bib_file, compile_tex_document, fix_latex, fix_percent
from ..config import INPUT_FILES


def keywords_node(state: GraphState, config: RunnableConfig):
    """
    This agent is in charge of getting the keywords for the paper
    """

    # temporary file with the selected keywords
    print("Finding keywords".ljust(33, '.'), end="", flush=True)
    f_temp = Path(f"{state['files']['Temp']}/Keywords.tex")

    if f_temp.exists():
        keywords = temp_file(state, f_temp, 'read')
        print('Found on Keywords.tex', end="", flush=True)

    else:

        if state['paper']['cmbagent_keywords']:
            ################ CMB Agent keywords ###############
            # Extract keywords
            PROMPT = cmbagent_keywords_prompt(state)
            keywords = cmbagent.get_keywords(PROMPT, n_keywords = 8)
        
            # Extract keys and join them with a comma.
            keywords = ", ".join(keywords.keys())
            ###################################################
        else:

            ################ Langgraph keywords ###############
            for attempt in range(3):  #try 3 times in case it fails

                print(f'{attempt} ', end="",flush=True)
                
                # Extract keywords
                PROMPT, keywords_list = keyword_prompt(state)
                state, result = LLM_call(PROMPT, state)
                keywords = extract_latex_block(state, result, "Keywords")
                
                # get the keywords and make a list with them
                input_keywords = [kw.strip() for kw in keywords.split(',') if kw.strip()]
            
                # Check which choosen keywords are actually AAS keywords
                matched_keywords = [kw for kw in input_keywords if kw in keywords_list]
                matched_keywords = ', '.join(matched_keywords)
                keywords = matched_keywords

                # get the number of keywords
                keywords = [item.strip() for item in keywords.split(',') if item.strip()]
                
                if len(keywords)>=state['params']['num_keywords']:
                    break
            else:
                print("Failed to get the keywords ",end="",flush=True)
                keywords = [""]
                state['params']['num_keywords'] = 0

            # take a random subset
            keywords = random.sample(keywords, state['params']['num_keywords'])

            # join all keywords into a string with comma separated
            keywords = ", ".join(keywords)
            ###################################################

        # write results to temporary file
        temp_file(state, f_temp, 'write', keywords)
        compile_tex_document(state, f_temp, state['files']['Temp'])

    minutes, seconds = divmod(time.time()-state['time']['start'], 60)
    print(" |  done ",end='')
    print(f"{state['tokens']['ti']} {state['tokens']['to']} [{int(minutes)}m {int(seconds)}s]")
    #print(f"  Selected keywords: {keywords} {state['tokens']['ti']} {state['tokens']['to']} [{int(minutes)}m {int(seconds)}s]")

    return {'paper': {**state['paper'], 'Keywords': keywords},
            'tokens': state['tokens']}


def abstract_node(state: GraphState, config: RunnableConfig):
    """
    This node gets the title and the abstract of the paper
    """

    # temporary file with the selected keywords
    print("Writing Abstract".ljust(33, '.'), end="", flush=True)
    f_temp1 = Path(f"{state['files']['Temp']}/Abstract.tex")
    f_temp2 = Path(f"{state['files']['Temp']}/Title.tex")

    # check if abstract already exists
    if f_temp1.exists():
        state['paper']['Abstract'] = temp_file(state, f_temp1, 'read')
        state['paper']['Title']    = temp_file(state, f_temp2, 'read')
        print('Found on Abstract.tex', end="", flush=True)

    else:
        # In case it fails, it has up to three attempts
        for attempt in range(5):
            print(f'{attempt} ', end="",flush=True)
            PROMPT = abstract_prompt(state, attempt)
            state, result = LLM_call(PROMPT, state)

            try:
                parsed_json = json_parser3(result)  #more stable than json_parser
                state['paper']['Title']    = parsed_json["Title"]
                state['paper']['Abstract'] = parsed_json["Abstract"]
                break  # success
            except Exception:
                time.sleep(2)
        else:
            fail_message = '''Tried 3 times but failed to extract the abstract. Recommendations:
                                - Run the paper writing module again
                                - If still fails, try using a more power LLM, e.g. gemini-2.5-pro
                            '''
            print(fail_message)
            raise RuntimeError("LLM failed to produce valid JSON after 3 attempts.")
    
        # perform self-reflections
        for i in range(1):

            # improve abstract
            PROMPT = abstract_reflection(state)
            state, result = LLM_call(PROMPT, state)
            state['paper']['Abstract'] = extract_latex_block(state, result, "Abstract")
            state['paper']['Abstract'] = fix_percent(state['paper']['Abstract']) #fix % by \%

        # save temporary file
        temp_file(state, f_temp2, 'write', state['paper']['Title'])
        temp_file(state, f_temp1, 'write', state['paper']['Abstract'])

        # compile title and abstract. If there are errors, try to fix them
        compile_tex_document(state, f_temp2, state['files']['Temp'])           #title
        success = compile_tex_document(state, f_temp1, state['files']['Temp']) #abstract
        if not(success):
            state['latex']['section_to_fix'] = 'Abstract'
            state, fixed = fix_latex(state, f_temp1)
            state['paper']['Abstract'] = fix_percent(state['paper']['Abstract']) #fix % by \%

    # Save paper and temporary file
    save_paper(state, state['files']['Paper_v1'])

    # print some information
    minutes, seconds = divmod(time.time()-state['time']['start'], 60)
    print(" |  done ",end='')
    print(f"{state['tokens']['ti']} {state['tokens']['to']} [{int(minutes)}m {int(seconds)}s]")

    return {'paper':{**state['paper'],
                     'Title':    state['paper']['Title'],
                     'Abstract': state['paper']['Abstract']},
            'tokens': state['tokens']}


def section_node(state: GraphState, config: RunnableConfig, section_name: str,
                 prompt_fn, reflection_fn=None):
    """
    This function generates a section of the paper
    Args:
      state: the state of the graph
      config: the config of the graph
      section_name: the name of the section to write
      prompt_fn: the prompt function for the section
      reflection_fn: whether to use self-reflections to improve the text
    """

    # temporary file with the selected keywords
    print(f'Writing {section_name}'.ljust(33, '.'), end="", flush=True)
    f_temp = Path(f"{state['files']['Temp']}/{section_name}.tex")

    # check if abstract already exists
    if f_temp.exists():
        state['paper'][section_name] = temp_file(state, f_temp, 'read')
        print(f'Found on {section_name}.tex', end="", flush=True)

    else:

        # Try for three times
        for attempt in range(3):

            print(f'{attempt} ', end="",flush=True)
            
            # --- Step 1: Prompt and parse section ---
            PROMPT = prompt_fn(state)
            state, result = LLM_call(PROMPT, state)
            section_text = extract_latex_block(state, result, section_name)
            state['paper'][section_name] = section_text
            
            # --- Step 2: Optional self-reflection ---
            if reflection_fn:
                for _ in range(2):
                    PROMPT = reflection_fn(state)
                    state, section_text = LLM_call(PROMPT, state)

            # --- Step 3: Check LaTeX ---
            section_text = LaTeX_checker(state, section_text)

            # --- Step 4: Remove unwanted LaTeX wrappers ---
            state['paper'][section_name] = clean_section(section_text, section_name)

            # --- Step 5: save file to file ---
            temp_file(state, f_temp, 'write', state['paper'][section_name])

            # --- Step 6: Compile and try to fix LaTeX errors ---
            if compile_tex_document(state, f_temp, state['files']['Temp']): #returns True if compiled properly
                break
            else:
                state['latex']['section_to_fix'] = f"{section_name}"
                state, fixed = fix_latex(state, f_temp)
                if fixed: #if fixed=True it means it fixed the error and compiled properly
                    break
        
    # Save paper
    save_paper(state, state['files']['Paper_v1'])

    # print some information
    minutes, seconds = divmod(time.time()-state['time']['start'], 60)
    print(" |  done ",end='')
    print(f"{state['tokens']['ti']} {state['tokens']['to']} [{int(minutes)}m {int(seconds)}s]")

    # return updated state
    return {"paper": {**state["paper"], section_name: state['paper'][section_name]},
            'tokens': state['tokens']}


# get the functions for the different nodes
def introduction_node(state: GraphState, config: RunnableConfig):
    return section_node(state, config, section_name="Introduction",
                        prompt_fn=introduction_prompt,
                        reflection_fn=introduction_reflection)

def methods_node(state: GraphState, config: RunnableConfig):
    return section_node(state, config, section_name="Methods",
                        prompt_fn=methods_prompt,
                        reflection_fn=None)

def results_node(state: GraphState, config: RunnableConfig):
    return section_node(state, config, section_name="Results",
                        prompt_fn=results_prompt,
                        reflection_fn=None)

def conclusions_node(state: GraphState, config: RunnableConfig):
    return section_node(state, config, section_name="Conclusions",
                        prompt_fn=conclusions_prompt,
                        reflection_fn=None)

#######################################################################################
def image_to_base64(image_path):
    ext = image_path.suffix.lower() #get the file extension
    if ext == '.pdf':
        # Convert first page of PDF to PNG bytes using PyMuPDF
        with fitz.open(str(image_path)) as doc:
            img_bytes = doc.load_page(0).get_pixmap().tobytes("png")
        data = img_bytes
    elif ext in {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}:
        with open(image_path, "rb") as file:
            data = file.read()
    else:
        raise ValueError(f"Unsupported image file: {image_path}")
    return base64.b64encode(data).decode('utf-8')


def plots_node(state: GraphState, config: RunnableConfig):
    """
    This function deals with the plots generated, processing all files in batches of 7
    """

    batch_size = 7 #number of images to process per LLM call
    folder_path = Path(f"{state['files']['Folder']}/{INPUT_FILES}/{state['files']['Plots']}")
    files = [f for f in folder_path.iterdir()
         if f.is_file() and f.name != '.DS_Store']
    num_images = len(files)

    # If more than 25, randomly select 25
    if num_images > 25:
        random.seed(1)  # for reproducibility
        files = random.sample(files, 25)
        num_images = 25

    # Process images in batches
    for start in range(0, num_images, batch_size):

        batch_files = files[start:start + batch_size]
        
        # temporary file with the images
        f_temp = Path(f"{state['files']['Temp']}/plots_{start+1}_{min(start+batch_size, num_images)}.json")

        if f_temp.exists():
            images = temp_file(state, f_temp, 'read', json_file=True)

        # get the caption for each image in the batch
        else:

            # do a loop over all images in the batch
            images = {}
            for i, file in enumerate(tqdm(batch_files, desc=f"Processing figures {start+1}-{min(start+batch_size, num_images)}")):
                image = image_to_base64(file)

                PROMPT = caption_prompt(state, image)
                state, result = LLM_call(PROMPT, state)
                caption = extract_latex_block(state, result, "Caption")
                caption = LaTeX_checker(state, caption)  #make sure is written in LaTeX
                images[f"image{i}"] = {'name': file.name, 'caption': caption}

            # save temporary json file with image name + image caption
            temp_file(state, f_temp, 'write', images, json_file=True)

        # temporary file with the images
        print(f'   Inserting figures {start+1}-{min(start+batch_size, num_images)}'.ljust(33,'.'), end="", flush=True)
        f_temp = Path(f"{state['files']['Temp']}/Results_{start+1}_{min(start+batch_size, num_images)}.tex")
        
        if f_temp.exists():
            state['paper']['Results'] = temp_file(state, f_temp, 'read')
            
        else:

            # sometimes it may not include the images. Give it three chances
            for attempt in range(3):

                print(f'{attempt} ', end="",flush=True)
                
                PROMPT = plot_prompt(state, images)
                state, result = LLM_call(PROMPT, state)
                results = extract_latex_block(state, result, "Section")

                # Check LaTeX
                results = LaTeX_checker(state, results)

                # --- Remove unwanted LaTeX wrappers ---
                state['paper']['Results'] = clean_section(results, 'Results')

                # check if the names of the images are the correct ones
                images_in_text = check_images_in_text(state, images)

                if images_in_text:
                    break
            else:
                raise RuntimeError("Unable to put the images in the text. Failed after three attemps")
                
            
            # save temporary file
            temp_file(state, f_temp, 'write', state['paper']['Results'])

            # save paper
            save_paper(state, state['files']['Paper_v1'])
            compile_tex_document(state, f_temp, state['files']['Temp']) #compile, but dont try to fix errors

        # print some information
        minutes, seconds = divmod(time.time()-state['time']['start'], 60)
        print(f" |  done {state['tokens']['ti']} {state['tokens']['to']} [{int(minutes)}m {int(seconds)}s]")

    # if the project has no images, no need to do this
    if num_images>0:
        
        # try to fix any errors in the Results in the last generated file
        print('Compiling text+figures'.ljust(33,'.'), end="", flush=True)
        success = compile_tex_document(state, f_temp, state['files']['Temp'])
        if not(success):
            state['latex']['section_to_fix'] = "Results"
            state, fixed = fix_latex(state, f_temp)
        minutes, seconds = divmod(time.time()-state['time']['start'], 60)
        print(f" |  done {state['tokens']['ti']} {state['tokens']['to']} [{int(minutes)}m {int(seconds)}s]")
    
    # compile paper
    compile_latex(state, state['files']['Paper_v1'])

    return {'paper':{**state['paper'], 'Results': state['paper']['Results']},
            'tokens': state['tokens']}



#######################################################################################
def refine_results(state: GraphState, config: RunnableConfig):
    """
    This agent takes the results section with plots and improves it
    """

    # if the number of plots is 0, just compile the existing version of the paper
    if state['files']['num_plots']==0:
        # save paper and compile it
        save_paper(state, state['files']['Paper_v2'])
        compile_latex(state, state['files']['Paper_v2'])
        return state
        
    
    # temporary file with the selected keywords
    print('Refining results'.ljust(33,'.'), end="", flush=True)
    f_temp = Path(f"{state['files']['Temp']}/Results_refined.tex")

    # check if this has already been done
    if f_temp.exists():
        state['paper']['Results'] = temp_file(state, f_temp, 'read')

    else:

        # try for 3 times in case its fails
        for attempt in range(3):

            print(f'{attempt} ', end="",flush=True)
        
            # Call the LLM to refine the results section
            PROMPT = refine_results_prompt(state)
            state, result = LLM_call(PROMPT, state)
            results = extract_latex_block(state, result, "Results")
        
            # Check LaTeX
            results = LaTeX_checker(state, results)
    
            # Remove unwanted LaTeX wrappers
            section_text = clean_section(results, 'Results')

            # Check that all references are done properly
            state['paper']['Results'] = check_references(state, section_text)

            # save temporary file
            temp_file(state, f_temp, 'write', state['paper']['Results'])

            # try to compile the paper
            if compile_tex_document(state, f_temp, state['files']['Temp']):
                break
            else:
                state['latex']['section_to_fix'] = "Results"
                state, fixed = fix_latex(state, f_temp)
                if fixed:
                    break

    # print some information
    minutes, seconds = divmod(time.time()-state['time']['start'], 60)
    print(f" |  done {state['tokens']['ti']} {state['tokens']['to']} [{int(minutes)}m {int(seconds)}s]")
            
    # save paper and compile it
    save_paper(state, state['files']['Paper_v2'])
    compile_latex(state, state['files']['Paper_v2'])

    return {'paper':{**state['paper'], 'Results': state['paper']['Results']},
            'tokens': state['tokens']}
    

def check_references(state: GraphState, text: str)-> str:
    """
    This function will check for wrong references to figures
    """

    PROMPT = references_prompt(state, text)
    state, result = LLM_call(PROMPT, state)
    section_text = extract_latex_block(state, result, "Text")

    return section_text
        
#######################################################################################
async def add_citations_async(state, text, section_name):
    """
    This is the actual function that calls perplexity and gets the new text 
    and the references.
    """
    f_temp1 = Path(f"{state['files']['Temp']}/{section_name}_w_citations.tex")
    f_temp2 = Path(f"{state['files']['Temp']}/{section_name}.bib")

    # check if this has already been done
    if f_temp1.exists():
        new_text   = temp_file(state, f_temp1, 'read')
        references = temp_file(state, f_temp2, 'read')

    else:
        
        loop = asyncio.get_event_loop()
        func = partial(process_tex_file_with_references, text, state["keys"])
        try:
            new_text, references = await loop.run_in_executor(None, func)
        except Exception as e:
            print(f"    {section_name} citations failed: {e}")
            return section_name, text, ""
        new_text = clean_section(new_text, section_name)

        # save temporary file
        temp_file(state, f_temp2, 'write', references)
        temp_file(state, f_temp1, 'write', new_text)
        
    print(f'    {section_name} done')
    return section_name, new_text, references

async def citations_node(state: GraphState, config: RunnableConfig):
    """
    This agent adds citations asynchronously to all main sections.
    """

    print("Adding citations...")

    if not state["keys"].PERPLEXITY:
        print("⚠️  PERPLEXITY_API_KEY not set; skipping citation insertion.")
        return {'paper': state['paper'],
                'tokens': state['tokens']}

    #sections = ['Introduction', 'Methods', 'Results', 'Conclusions']
    sections = ['Introduction', 'Methods']
    tasks = [add_citations_async(state, state['paper'][section], section) for section in sections]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Deduplicate full BibTeX entries
    bib_entries_set = set()
    bib_entries_list = []

    for result in results:
        if isinstance(result, Exception):
            print(f"⚠️  Citation task failed: {result}")
            continue

        section_name, updated_text, references = result

        state['paper'][section_name] = updated_text

        # Break the full .bib string into entries by \n\n
        entries = references.strip().split('\n\n')
        for entry in entries:
            clean_entry = entry.strip()
            if clean_entry and clean_entry not in bib_entries_set:
                bib_entries_list.append(clean_entry)

    # Save all combined deduplicated BibTeX entries as a single string
    state['paper']['References'] = "\n\n".join(bib_entries_list)

    # save paper and bibliography
    save_paper(state, state['files']['Paper_v3'])
    save_bib(state)

    # sanitize bibliography
    process_bib_file(f"{state['files']['Paper_folder']}/bibliography_temp.bib",
                     f"{state['files']['Paper_folder']}/bibliography.bib")
    print("✅ Citations added to all sections.")

    # compile latex
    compile_latex(state, state['files']['Paper_v3'])

    # make a last clean up of the sections
    print("Making a final check to the sections...")
    for section_name in sections:

        f_temp = Path(f"{state['files']['Temp']}/{section_name}_w_citations2.tex")

        # check if this has already been done
        if f_temp.exists():
            section_text = temp_file(state, f_temp, 'read')
        else:
            PROMPT = clean_section_prompt(state, state['paper'][section_name])
            state, result = LLM_call(PROMPT, state)
            section_text = extract_latex_block(state, result, "Text")
            section_text = LaTeX_checker(state, section_text)          #check LaTeX
            section_text = clean_section(section_text, section_name)   #remove unwanted LaTeX text
            temp_file(state, f_temp, 'write', section_text)
            
        state['paper'][section_name] = section_text
    save_paper(state, state['files']['Paper_v4'])
    compile_latex(state, state['files']['Paper_v4'])

    return {'paper': state['paper'],
            'tokens': state['tokens']}
#######################################################################################
