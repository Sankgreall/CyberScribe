from setuptools import setup, find_packages

setup(
    name='CyberScribe',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        "openai",
        "python-dotenv",
        "tenacity",
        "argparse",
        "python-docx",
        "pydub",
        "nltk",
        "tiktoken",
        "PyPDF2",
        "openpyxl",
        "pandas"
    ],
    package_data={
        'document_prompt': ['prompts/document.prompt'],
        'merge_prompt': ['prompts/merge.prompt'],
    }
)