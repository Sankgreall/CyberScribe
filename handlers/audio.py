from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from openai import OpenAI
import os
import io
import tempfile
from scipy.io import wavfile
import threading
import queue
from pydub import AudioSegment
from pyannote.audio import Pipeline
from pyannote.core import Segment, Annotation, Timeline
import torchaudio
import whisper
import tempfile
from utils import *
import subprocess
from pathlib import Path



SAMPLE_RATE = 44100  # Sample rate
DEFAULT_SILENCE_DURATION = 1  # Default silence duration
SLEEP_INTERVAL = 0.1  # Sleep interval to avoid busy waiting
PUNC_SENT_END = ['.', '?', '!']

class AudioHandler:

    MAX_SIZE = 24 * 1024 * 1024  # Roughly 24MB
    MIN_SILENCE_LENGTH = 450  # 500 milliseconds
    SILENCE_THRESH = -40  # -40 dB

    def __init__(self):

        # Recording flags
        self.sample_rate = 44100
        self.audio = []
        self.silence_duration = 0
        self.is_recording = False
        self.background_noise_level = None
        self.background_samples = []
        self.stop_recording_flag = threading.Event()
        self.audio_queue = queue.Queue()
        self.MIN_CHUNK_DURATION = 5  # Minimum chunk duration in seconds
        self.MAX_CHUNK_DURATION = 60  # Maximum chunk duration in seconds

        # Instantiate new OpenAI client
        self.openai_client = OpenAI(
            api_key=os.environ.get('OPENAI_API_KEY'),
        )

    def convert_to_wav(self, file_path):
        """
        Converts an audio file to WAV format using FFmpeg.
        """
        if not Path(file_path).is_file():
            print(f"File not found: {file_path}")
            return

        # Check if the file is already a WAV file
        if file_path.lower().endswith('.wav'):
            print(f"The file is already a WAV: {file_path}")
            return

        # Creating a temporary file for the output
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            output_file = temp_file.name

        # FFmpeg command for conversion
        command = f'ffmpeg -i "{file_path}" "{output_file}" -y'
        
        try:
            subprocess.run(command, check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Converted to WAV: {output_file}")
            return output_file
        except subprocess.CalledProcessError as e:
            print(f"Error during conversion: {e}")
            os.remove(output_file)  # Cleanup if conversion fails
            return None

    def get_max_size(self):
        return self.MAX_SIZE
    
    def convert_seconds_to_hms_ms(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds_int = int(seconds % 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds_int:02d}.{milliseconds:03d}"

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
    
    def transcribe_audio(self, file_path):

        try:
        
            torchaudio.set_audio_backend("soundfile")
            conversion_flag = False

            # Check if we are already dealing with a .wav
            if not file_path.lower().endswith('.wav'):
                print("File requires conversion to WAV.")
                # Convert to WAV
                file_path = self.convert_to_wav(file_path)
                conversion_flag = True

            # Load diairization model
            pipeline = Pipeline.from_pretrained(
                'pyannote/speaker-diarization-3.1',
                use_auth_token=os.environ.get('HUGGINGFACE_TOKEN')
            )

            # Perform speaker diarization
            print("Performing speaker diarization...")
            diarization_result = pipeline(file_path)

            # FOR TESTING
            # newAudio = AudioSegment.from_wav(file_path)
            # a = newAudio[0:1 * 60 * 1000]
            # a.export('temp.wav', format="wav")
            # file_path = 'temp.wav'

            if os.environ.get('WHISPER_TYPE') == "local":
                print("Loading Whipser model")
                model = whisper.load_model(os.environ.get('WHISPER_LOCAL_MODEL'))

            dz_results = []
            for segment, index, speaker in diarization_result.itertracks(yield_label=True):

                # Check if the preceding speaker is the same
                if len(dz_results) > 0 and dz_results[-1]['speaker'] == speaker:
                    # If so, extend the previous segment with the new end
                    dz_results[-1]['end'] = segment.end
                else:
                    dz_results.append({
                        'start': segment.start,
                        'end': segment.end,
                        'speaker': speaker,
                    })
            

            print("Transcribing audio...")
            for index, segment in enumerate(dz_results):
                newAudio = AudioSegment.from_wav(file_path)
                
                # Calculating start and end times
                start = int(segment['start'] * 1000)
                end = int(segment['end'] * 1000)    

                # Make sure delta time is > 0.1
                if end - start >= 150:
                    audio_segment = newAudio[start:end]

                    # Generate a unique temporary file name
                    temp_file_path = tempfile.mktemp(suffix=".wav")

                    # Manually manage the temporary file
                    try:
                        # Export audio segment to the temporary file
                        audio_segment.export(temp_file_path, format="wav")

                        with open(temp_file_path, "rb") as audio_file:
                            transcript = self.openai_client.audio.transcriptions.create(
                                model="whisper-1", 
                                file=audio_file, 
                                response_format="json",
                                language="en",
                            )

                            # Update dz_results directly
                            dz_results[index]['transcript'] = transcript.text

                    finally:
                        # Ensure the temporary file is deleted
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)

            # Handle the results
            for line in dz_results:
                
                output_file_name = f"{process_filename(file_path)}-transcript.txt"
                folder="./output"

                # Create the output directory if it doesn't exist
                if not os.path.exists(f"{folder}"):
                    os.makedirs(f"{folder}")
                    
                # Create the complete path to the file
                filepath = os.path.join(f"{folder}", output_file_name)

                with open(filepath, 'a') as file:

                    if 'transcript' not in line or line['transcript'] == "":
                        continue
                    
                    speaker_info = f"{line['speaker']}: {self.convert_seconds_to_hms_ms(line['start'])} --> {self.convert_seconds_to_hms_ms(line['end'])}"
                    transcript = line['transcript']

                    file.write(speaker_info + "\n")
                    file.write(transcript + "\n\n")

            print(f"Saved transcript to {filepath}")
            return {"output_file": filepath, "object": dz_results}

        finally:
            # Remove the temporary file if it exists
            if conversion_flag:
                os.remove(file_path)

        

