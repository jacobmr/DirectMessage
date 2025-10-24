"""
HIPAA Direct Messaging Framework
Python package for HIPAA-compliant Direct message sending and receiving
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
try:
    long_description = (this_directory / "README.md").read_text()
except:
    long_description = "HIPAA-compliant Direct messaging framework with IMAP and phiMail support"

setup(
    name="hipaa-direct",
    version="1.0.0",
    author="JMR / ResearchFlo",
    description="HIPAA-compliant Direct messaging framework with IMAP and phiMail support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jacobmr/DirectMessage",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Topic :: Communications :: Email",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "cryptography>=41.0.0",
        "pyOpenSSL>=23.0.0",
        "python-dotenv>=1.0.0",
        "email-validator>=2.0.0",
        "requests>=2.31.0",
        "certifi>=2023.7.22",
    ],
    extras_require={
        "fastapi": [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "pydantic>=2.0.0",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
        ],
    },
    keywords="hipaa direct-messaging healthcare imap phimail fastapi",
    project_urls={
        "Documentation": "https://github.com/jacobmr/DirectMessage/blob/main/README.md",
        "Source": "https://github.com/jacobmr/DirectMessage",
        "Bug Reports": "https://github.com/jacobmr/DirectMessage/issues",
    },
)
