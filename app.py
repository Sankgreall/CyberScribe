import os
import argparse
from dotenv import load_dotenv

# Import handler classes
from handlers.ai import OpenAIWrapper

# Import utils
from utils import *

# Load environment variables from .env file
load_dotenv()

def parse_args():
    parser = argparse.ArgumentParser(description='Generate notes from audio, text transcription, or documents.')
    parser.add_argument('--doc', help='Path(s) to the document(s) for summarisation.', type=str, action='append', default=[])
    parser.add_argument("--query", help="Query string. Defaults to None if not provided.", type=str, default=None)
    args = parser.parse_args()

    for doc_path in args.doc:
        if not os.path.isfile(doc_path):
            parser.error(f"The file '{doc_path}' does not exist.")

    return args

def main():

    # Load args
    args = parse_args()

    # Load AI class
    openai_wrapper = OpenAIWrapper()

    # Define constants
    summary = ""

    # Merge notes with context from the provided documents
    if args.doc:
        print("Summarising notes from documents...")
        merged_document_summary = ""
        summaries = []

        for doc in args.doc:
            print(f"Summarising {doc}...")
            summaries.append(openai_wrapper.summarise_document(doc, args.query))

        print("Merging summaries into notes...")
        merge_prompt = ""
        merge_chunks = []
        for index, summary in enumerate(summaries):
            # Construct master prompt
            new_document = ""
            new_document += f"{doc} summary:\n"
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
            full_summary = openai_wrapper.submit_to_openai("./prompts/merge.prompt", merge_prompt)

        # We iterate summaries
        else:
            print("Summarising incrementally due to small context window...")
            full_summary = ""
            for chunk in merge_chunks:
                full_summary = full_summary + chunk
                full_summary = openai_wrapper.submit_to_openai("./prompts/merge.prompt", full_summary)

        # Write to file
        write_to_file("notes.txt", full_summary)

    print("Done!")


if __name__ == "__main__":
    main()
