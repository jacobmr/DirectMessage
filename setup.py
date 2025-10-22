from setuptools import setup, find_packages

setup(
    name="hipaa-direct-messaging",
    version="0.1.0",
    description="HIPAA-compliant Direct Messaging framework",
    author="JMR",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "cryptography>=41.0.0",
        "pyOpenSSL>=23.0.0",
        "python-dotenv>=1.0.0",
        "email-validator>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
        ],
    },
)
