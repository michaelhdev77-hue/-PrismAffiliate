from setuptools import setup, find_packages

setup(
    name="prism-affiliate-shared",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.27.0",
        "cryptography>=42.0.0",
        "pydantic>=2.0.0",
        "tenacity>=8.2.0",
    ],
)
