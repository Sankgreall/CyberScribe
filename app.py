import os
import argparse
from dotenv import load_dotenv

# Import handler classes
from handlers.ai import OpenAIWrapper

# Import utils
if __name__ == "__main__":
    from utils import *
else:
    from CyberScribe.utils import *

# Load environment variables from .env file
load_dotenv()

def parse_args(doc_paths, query=None):
    for doc_path in doc_paths:
        if not os.path.isfile(doc_path):
            raise FileNotFoundError(f"The file '{doc_path}' does not exist.")

    if query is None or query.strip() == "":
        query = os.getenv('QUERY')
        print("Query loaded from .env file!")
        
    return doc_paths, query

def summarise_documents(doc_paths, query):
    # Load AI class
    openai_wrapper = OpenAIWrapper()

    print("Summarising notes from documents...")
    summaries = []

    for doc in doc_paths:
        print(f"Summarising {doc}...")
        summaries.append(openai_wrapper.summarise_document(doc, query))
    
    return summaries

def generate_notes(doc_paths, query=None, transcribe=False, return_text=False):

    doc_paths, query = parse_args(doc_paths, query)

    # Load AI class
    openai_wrapper = OpenAIWrapper()

    if not transcribe:

        summaries = summarise_documents(doc_paths, query)

        print("Merging summaries into notes...")
        merge_prompt = ""
        merge_chunks = []
        for index, summary in enumerate(summaries):
            # Construct master prompt
            new_document = ""
            new_document += f"{doc_paths[index]} summary:\n"
            new_document += f"{summary}"

            if index < len(summaries) - 1:
                new_document += "\n\n--\n\n"

            # Count total tokens for the prompt
            total_tokens = count_tokens(merge_prompt + new_document)

            # This ensures success, as we need to leave room for the returned sumary + the summary from the previous iteration
            if total_tokens < (int(os.getenv('MAX_CONTEXT')) - int(os.getenv('MAX_SUMMARY_LENGTH'))):
                # Proceed as usual
                merge_prompt = merge_prompt + new_document
                pass
            else:
                # Add the current merge chunk onto an array, and start new chunk
                merge_chunks.append(merge_prompt)
                merge_prompt = new_document
                # Continue the loop
                pass

        # Submit summaries
        if len(merge_chunks) == 0:
            full_summary = openai_wrapper.submit_to_openai("merge", merge_prompt)

        # We iterate summaries
        else:
            print("Summarising incrementally due to small context window...")
            full_summary = ""
            for chunk in merge_chunks:
                full_summary = full_summary + chunk
                full_summary = openai_wrapper.submit_to_openai("merge", full_summary)

        # Check if the function should return the text or write it to a file
        if return_text:
            return full_summary
        else:
            write_to_file("notes.txt", full_summary)
            print("Done!")

        print("Done!")

    # Just create transcripts
    # TODO: return data in line with return_text flag above
    else:
        for doc in doc_paths:
            print(f"Transcribing {doc}...")
            full_summary = openai_wrapper.transcribe(doc)
            file_name = doc.split('\\')[-1].split('.')[0]
            write_to_file(f"transcription.txt", full_summary)
            print(file_name)



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Generate notes from audio, text transcription, or documents.')
    parser.add_argument('--doc', help='Path(s) to the document(s) for summarisation.', type=str, action='append', default=[])
    parser.add_argument('--transcribe', help='Set to true if input is a transcript.', action='store_true')
    parser.add_argument("--query", help="Query string. Defaults to None if not provided.", type=str, default=None)
    
    args = parser.parse_args()
    generate_notes(args.doc, args.query, args.transcribe)