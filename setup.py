"""Setup script for PawConnect AI."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read base requirements (excluding heavy ML dependencies for webhook deployment)
base_requirements = [
    "python-dotenv>=1.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "email-validator>=2.0.0",
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "aiohttp>=3.9.0",
    "httpx>=0.25.0",
    "requests>=2.31.0",
    "google-cloud-firestore>=2.13.0",
    "google-cloud-vision>=3.5.0",
    "google-cloud-pubsub>=2.18.0",
    "loguru>=0.7.2",
    "numpy>=1.26.0",
    "python-dateutil>=2.8.2",
]

# Heavy ML dependencies (optional)
ml_requirements = [
    "tensorflow>=2.15.0",
    "scikit-learn>=1.3.2",
    "pandas>=2.1.0",
    "transformers>=4.35.0",
    "torch>=2.1.0",
]

# Additional dependencies for full installation
full_requirements = base_requirements + ml_requirements + [
    "google-cloud-aiplatform>=1.38.0",
    "google-cloud-dialogflow-cx>=1.20.0",
    "google-cloud-storage>=2.14.0",
    "google-cloud-translate>=3.13.0",
    "google-cloud-speech>=2.23.0",
    "marshmallow>=3.20.0",
    "asyncio>=3.4.3",
    "aiofiles>=23.2.1",
    "redis>=5.0.1",
    "sqlalchemy>=2.0.23",
    "psycopg2-binary>=2.9.9",
    "python-json-logger>=2.0.7",
    "pytz>=2023.3",
    "geopy>=2.4.1",
    "pillow>=10.1.0",
]

setup(
    name="pawconnect-ai",
    version="1.0.0",
    author="Lee Whieldon",
    author_email="lwhieldon1@gmail.com",
    description="Multi-agent system for intelligent pet foster and adoption matching",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Lwhieldon/PawConnect",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=base_requirements,
    extras_require={
        "ml": ml_requirements,
        "full": full_requirements,
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
            "responses>=0.24.1",
            "faker>=20.1.0",
            "freezegun>=1.4.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "pawconnect=pawconnect_ai.agent:main",
        ],
    },
)
