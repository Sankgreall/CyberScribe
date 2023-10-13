import os
import pandas as pd
import openai
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from handlers.document import DocumentHandler
from handlers.audio import AudioHandler
from utils import *

class OpenAIWrapper:

    def __init__(self):

        # Configure OpenAI
        if os.getenv("AI_TYPE") == "azure":
            openai.api_key = os.getenv("OPENAI_API_KEY")
            openai.api_base = f"https://{os.getenv('AZ_RESOURCE')}.openai.azure.com"
            openai.api_type = os.getenv("AI_TYPE")
            openai.api_version = os.getenv('AZ_VERSION')
            pass

        elif os.getenv("AI_TYPE") == "openai":
            openai.api_key = os.getenv("OPENAI_API_KEY")
            pass

        else:
            print(f"Unknown AI type: {os.getenv('AI_TYPE')}. Exiting...")
            exit(1)

        # Init variables from environment
        self.MODEL = os.getenv("MODEL")
        self.TEMPERATURE=float(os.getenv("TEMPERATURE"))
        self.MAX_CONTEXT = int(os.getenv("MAX_CONTEXT"))
        self.MAX_SUMMARY_LENGTH = int(os.getenv("MAX_SUMMARY_LENGTH"))

        # Init document handler
        self.document_handler = DocumentHandler()
        self.audio_handler = AudioHandler()

    def get_system_prompt(self, file_path, placeholders={}):
        with open(file_path, 'r') as f:
            system_prompt = f.read().strip()
            if placeholders:
                system_prompt = system_prompt.format(**placeholders)
        return system_prompt
    
    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=2, max=30), 
        retry=retry_if_exception_type(Exception),
        retry_error_callback=retry_error_callback
    )
    def submit_to_openai(self, system_prompt_path, user_content, placeholders={}):

        # Set the max context length of the summary
        placeholders['max_length'] = self.MAX_SUMMARY_LENGTH

        # Get the system prompt
        system_prompt = self.get_system_prompt(system_prompt_path, placeholders)

        prompt = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        }

        if os.getenv('AI_TYPE') == "azure":
            # Do things differently, because they SUCK
            response = openai.ChatCompletion.create(engine=self.MODEL, temperature=self.TEMPERATURE, **prompt)

        else:
            response = openai.ChatCompletion.create(model=self.MODEL, temperature=self.TEMPERATURE, **prompt)

        return response.choices[0].message.content
    
    def summarise_document(self, doc_path, query=None, summary=""):

        # If document is Excel
        if doc_path.endswith('.xlsx'):
            df = pd.read_excel(doc_path)
            df = df.dropna(how='all')
            chunks = self.document_handler.chunk_spreadsheet(df, self.MAX_SUMMARY_LENGTH)
            
            # Convert each chunk into raw text format
            chunks_as_text = ["\n".join("\t".join(str(cell) for cell in row) for row in chunk) for chunk in chunks]
            
        # If document is PDF
        elif doc_path.endswith('.pdf'):
            text = extract_text_from_pdf(doc_path)
            chunks_as_text = self.document_handler.chunk_text(text, self.MAX_SUMMARY_LENGTH)
            
        # If document is Word
        elif doc_path.endswith('.docx'):
            text = extract_text_from_docx(doc_path)
            chunks_as_text = self.document_handler.chunk_text(text, self.MAX_SUMMARY_LENGTH)

        elif doc_path.endswith('.txt'):
            text = read_text_file(doc_path)
            chunks_as_text = self.document_handler.chunk_text(text, self.MAX_SUMMARY_LENGTH)

        elif is_audio_file(doc_path):
            file_size = os.path.getsize(doc_path)
            print("Transcribing audio...")

            if file_size >= self.audio_handler.get_max_size():
                transcription = self.audio_handler.transcribe_large_audio(doc_path)
            else:
                transcription = self.audio_handler.transcribe_audio(doc_path)

            # Chunk
            chunks_as_text = self.document_handler.chunk_text(transcription, self.MAX_SUMMARY_LENGTH)
            
        # We have an array of chunks, now we need to summarise each chunk and merge into a master summary
        if len(chunks_as_text) > 1:
            print("Chunking document...")

        for chunk in chunks_as_text:
                
                # Construct AI request
                request = f"{doc_path} summary:\n\n{summary}\n\n--\n\nNext chunk:\n\n{chunk}"
                if query:
                    request += f"\n\n--\n\nUser query: {query}"

                summary = self.submit_to_openai('./prompts/document.prompt', request)


        return summary
        
    
    def summarize_iteratively(self, transcription_chunks):
        summary = ""
        for chunk in transcription_chunks:
            combined_text = summary + " " + chunk 
            summary = self.get_summary_from_gpt4(combined_text)
        return summary