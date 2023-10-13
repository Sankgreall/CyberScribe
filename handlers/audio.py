from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import openai
import os
import io

class AudioHandler:

    MAX_SIZE = 24 * 1024 * 1024  # Roughly 24MB
    MIN_SILENCE_LENGTH = 500  # 500 milliseconds
    SILENCE_THRESH = -40  # -40 dB

    def get_max_size(self):
        return self.MAX_SIZE

    def split_audio_on_silence(self, audio_chunk):
        """Splits an audio chunk around a desired length, preferring silence periods."""
        print("Audio file is large. Splitting audio on silence...")
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

        # Extract the file extension
        file_extension = os.path.splitext(file_path)[1][1:]

        print(f"Identified audio file: {file_extension}")

        # Read the audio file with the correct format
        audio = AudioSegment.from_file(file_path, format=file_extension)
        total_transcription = ""

        while len(audio) > 0:
            chunk, audio = self.split_audio_on_silence(audio)
            chunk_stream = io.BytesIO()
            chunk.export(chunk_stream, format="mp3")
            chunk_stream.seek(0)

            print("Submitting to OpenAI Whisper...")
            response = openai.Audio.transcribe("whisper-1", chunk_stream)
            if 'text' in response:
                total_transcription += response['text'] + " "
            else:
                raise ValueError("Failed to transcribe an audio chunk")

        return total_transcription
    
    @staticmethod
    def transcribe_audio(file_path):
        with open(file_path, "rb") as audio_file:
            response = openai.Audio.transcribe("whisper-1", audio_file)
            if 'text' in response:
                return response['text']
            else:
                raise ValueError("Failed to transcribe audio")