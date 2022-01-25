from setuptools import setup, find_packages

setup(
    name='unsigned_bot',
    version='0.0.7',
    packages=find_packages(),
    install_requires = [
        "aiohttp",
        "discord.py",
        "discord-py-slash-command",
        "lxml",
        "numpy",
        "Pillow",
        "python-dateutil",
        "python-dotenv",
        "ratelimit",
        "requests",
        "requests-html",
        "tweepy"
    ]
)