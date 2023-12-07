# CyberScribe
CyberScribe is a Python-based tool designed to summarise large volumes of text from multiple data sources. Engineered to work with both OpenAI and Azure OpenAI deployments, this tool is ideal for researchers, professionals, or anyone needing to distil key points from diverse data sources.

## Features
- Supports multiple file types including PDF, DOCX, XLSX, Plaintext, and Audio files.
- Audio files are transcribed with speaker diarization
- Query-based summarisation for targeted results.
- Supports both OpenAI and Azure OpenAI deployments.
- Can be invoked as a script or loaded as a library for use in other applications

## AI Accuracy Warning
⚠️ CyberScribe leverages OpenAI models and other AI technologies with prompts designed to provide accurate and relevant summarisations. However, it's important to note that the tool is not infallible. Users should exercise critical thinking and discretion when interpreting results. The summarisation techniques may not capture nuances or context in the same way a human would, and there may be variations in accuracy depending on the quality and complexity of the original text sources.


## Requirements
- Python 3.x

## Installation

```bash
git clone https://github.com/Sankgreall/CyberScribe
cd CyberScribe
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the root directory based on the `.env.sample`. Update the variables per your requirements. The table below explains each environment variable:

| Variable             | Description                                                  | Recommended Value      |
|----------------------|--------------------------------------------------------------|------------------------|
| `AI_TYPE`            | AI Service ('azure' or 'openai')                             |                        |
| `OPENAI_API_KEY`     | OpenAI or Azure API key                                      |                        |
| `AZ_VERSION`         | Azure API version                                            | '2023-08-01-preview'   |
| `AZ_RESOURCE`        | Name of Azure OpenAI resource                                |                        |
| `MODEL`              | Model to use                                                 | 'gpt-4-32k'            |
| `MAX_CONTEXT`        | Maximum context size                                         | 29000                  |
| `MAX_SUMMARY_LENGTH` | Maximum summary length                                       | 2500                   |
| `TEMPERATURE`        | Model's temperature                                          | 0.2                    |
| `WHISPER_TYPE`       | Whisper type for audio transcriptions                        | 'local'                |
| `WHISPER_LOCAL_MODEL`| Local Whisper model to use                                   | 'tiny'                 |
| `HUGGINGFACE_TOKEN`  | Token for Huggingface integrations                           |                        |


## Usage

### Summarise Multiple Documents

```bash
python main.py --doc "/path/to/document.docx" --doc "/path/to/meeting_recording.mp3"
```

### Query-based Summarisation

```bash
python main.py --doc "/path/to/document.docx" --doc "/path/to/meeting_recording.mp3" --query "your query here"
```

### Transcription

```bash
python main.py --transcribe "/path/to/meeting_recording.mp3"
```

## Contributions
Feel free to contribute to this project by opening issues or submitting pull requests.

## Licence
This project is licenced under the MIT Licence - see the [LICENCE.md](LICENCE.md) file for details.
