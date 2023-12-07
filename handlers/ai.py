import os
import pandas as pd
from openai import OpenAI
from openai import AzureOpenAI
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from handlers.document import DocumentHandler
from handlers.audio import AudioHandler
import sys
import pkg_resources

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils import *
except ImportError:
    from CyberScribe.utils import *

class OpenAIWrapper:

    def __init__(self):

        # Instantiate new OpenAI client
        # Configure Azure
        if os.getenv("AI_TYPE") == "azure":
            self.openai_client = AzureOpenAI(
                api_key=os.environ.get('AZURE_OPENAI_API_KEY'),
                azure_endpoint=f"https://{os.environ.get('AZ_RESOURCE')}.openai.azure.com",
                api_version=os.environ.get('AZ_VERSION')
            )

        # Configure OpenAI
        elif os.getenv("AI_TYPE") == "openai":
            self.openai_client = OpenAI(
                api_key=os.environ.get('OPENAI_API_KEY'),
            )

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

    def get_system_prompt(self, prompt_resource, placeholders={}):

        # Try package resource first
        try:
            file_path = pkg_resources.resource_filename("CyberScribe", f"prompts/{prompt_resource}.prompt")

        # Then fall back to relative path
        except Exception:
            file_path = f"./prompts/{prompt_resource}.prompt"

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
    def submit_to_openai(self, system_prompt_name, user_content, placeholders={}):

        # Set the max context length of the summary
        placeholders['max_length'] = self.MAX_SUMMARY_LENGTH

        # Get the system prompt
        system_prompt = self.get_system_prompt(system_prompt_name, placeholders)

        prompt = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        }

        # Submit to OpenAI
        response = self.openai_client.ChatCompletion.create(model=self.MODEL, temperature=self.TEMPERATURE, **prompt)

        return response.choices[0].message.content
    
    def transcribe(self, doc_path):

        if is_audio_file(doc_path):
            transcription = self.audio_handler.transcribe_audio(doc_path)

        return transcription
    
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

            print("Transcribing audio...")
            transcription = self.audio_handler.transcribe_audio(doc_path)

            # Load data from file
            transcription = read_text_file(transcription['output_file'])

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

                summary = self.submit_to_openai('document', request)


        return summary
        
    
    def summarize_iteratively(self, transcription_chunks):
        summary = ""
        for chunk in transcription_chunks:
            combined_text = summary + " " + chunk 
            summary = self.get_summary_from_gpt4(combined_text)
        return summary