from setuptools import setup, find_packages

setup(
    name='CyberScribe',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        "openai<2",
        "python-dotenv",
        "tenacity",
        "argparse",
        "python-docx",
        "pydub",
        "nltk",
        "tiktoken",
        "PyPDF2",
        "rx",
        "sounddevice",
        "numpy",
        "pandas",
        "diart",
        "scipy",
        "pyannote.audio",
        "torchaudio",
        "torch",
        "openai-whisper",
        "pycryptodome"
    ],
    package_data={
        'CyberScribe': ['prompts/document.prompt', 'prompts/merge.prompt'],
    }
)
