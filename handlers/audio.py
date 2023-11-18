from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import openai
import os
import io
import tempfile


class AudioHandler:

    MAX_SIZE = 24 * 1024 * 1024  # Roughly 24MB
    MIN_SILENCE_LENGTH = 500  # 500 milliseconds
    SILENCE_THRESH = -40  # -40 dB

    def __del__(self):
        # Reset openai properties
        openai.api_base = self.original_api_base
        openai.api_type = self.original_api_type
        openai.api_version = self.original_api_version

    def __init__(self):

        # Store original OpenAI properties to avoid conflicting with other packages
        self.original_api_base = openai.api_base
        self.original_api_type = openai.api_type
        self.original_api_version = openai.api_version

        # Overwrite with OpenAI API key
        openai.api_key = os.getenv("OPENAI_API_KEY")
        openai.api_base = "https://api.openai.com/v1"
        openai.api_type = "open_ai"
        openai.api_version = None

    def get_max_size(self):
        return self.MAX_SIZE

    def split_audio_on_silence(self, audio_chunk):
        """Splits an audio chunk around a desired length, preferring silence periods."""
        desired_length_ms = int(self.MAX_SIZE / audio_chunk.frame_rate / audio_chunk.frame_width) * 1000
        nonsilent_chunks = detect_nonsilent(audio_chunk, self.MIN_SILENCE_LENGTH, self.SILENCE_THRESH)
        split_point = None
        for start, end in nonsilent_chunks:
            if start > desired_length_ms:
                break
            split_point = end

        if split_point is None:
            return audio_chunk, AudioSegment.empty()

        return audio_chunk[:split_point], audio_chunk[split_point:]
    
    def transcribe_large_audio(self, file_path):

        print("Audio file is large. Splitting audio on silence...")

        # Extract the file extension
        file_extension = os.path.splitext(file_path)[1][1:]

        print(f"Identified audio file: {file_extension}")

        # Read the audio file with the correct format
        audio = AudioSegment.from_file(file_path, format=file_extension)
        total_transcription = ""

        while len(audio) > 0:
            chunk, audio = self.split_audio_on_silence(audio)

            # Create a temporary file and immediately close it to avoid locking issues
            temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_file_path = temp_file.name
            temp_file.close()

            try:
                # Export the audio chunk to the temporary file
                chunk.export(temp_file_path, format="mp3")
                
                print("Submitting to OpenAI Whisper...")
                # Open the temporary file in read-binary mode
                with open(temp_file_path, "rb") as file_stream:
                    response = openai.Audio.transcribe("whisper-1", file_stream)
                    if 'text' in response:
                        total_transcription += response['text'] + " "
                    else:
                        raise ValueError("Failed to transcribe an audio chunk")
            finally:
                # Clean up the temporary file
                os.remove(temp_file_path)

        return total_transcription
    
    @staticmethod
    def transcribe_audio(file_path):
        with open(file_path, "rb") as audio_file:
            response = openai.Audio.transcribe("whisper-1", audio_file)
            if 'text' in response:
                return response['text']
            else:
                raise ValueError("Failed to transcribe audio")