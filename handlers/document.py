import os
import nltk

# Download required libraries
nltk.download('punkt', quiet=True)
class DocumentHandler:

    def __init__(self):

        # Init variables from environment

        self.MAX_CONTEXT = int(os.getenv("MAX_CONTEXT"))

    def chunk_spreadsheet(self, df, token_count):
        """Splits a DataFrame into chunks based on a token limit."""

        # Get the max content from the AI class
        max_tokens = self.MAX_CONTEXT

        # Calculate max tokens to submit per chunk
        token_limit = max_tokens - token_count

        chunks = []
        current_chunk = []
        current_token_count = 0

        # Include headers in the token count
        header_token_count = sum(len(str(header).split()) for header in df.columns)

        for index, row in df.iterrows():
            row_token_count = sum(len(str(cell).split()) for cell in row)

            # Check if adding this row exceeds the token limit
            if current_token_count + row_token_count + header_token_count > token_limit:
                chunks.append(current_chunk)
                current_chunk = []
                current_token_count = 0

            current_chunk.append(row.tolist())
            current_token_count += row_token_count

        # Add any remaining rows to the last chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks
    
    def chunk_text(self, text, token_count):

        # Get the max content from the AI class
        max_tokens = self.MAX_CONTEXT

        # Calculate max tokens to submit per chunk
        token_limit = max_tokens - token_count

        # Split the text into sentences
        sentences = nltk.sent_tokenize(text)
        chunks = []
        current_chunk = []

        for sentence in sentences:
            # Check if adding a new sentence to the current chunk would exceed the token limit
            if len(" ".join(current_chunk + [sentence])) > token_limit:
                # If so, add the current chunk to the list of chunks and start a new one with the current sentence
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
            else:
                # If not, add the sentence to the current chunk
                current_chunk.append(sentence)

        # If there's an unfinished chunk left, add it to the list of chunks
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks