# Cryptomemebot

Cryptomembot is a friendly bot that pulls the top memes from `r/cryptocurrencymemes` and posts them to your telegram group. You can also command the bot by sending it messages and have a basic conversation with it.

## Telegram commands
- `/meme` : Fetch a crypto meme
- `/dailymeme`: Fetch a meme daily at 9:30 AM
- `/dailymemestop`: Stop fetching daily memes
- `/conversationstart`: Start talking with an ML chatbot
- `/conversationstop`: Stop the chatbot
- `/help`: Help page with all commands

## Installation
1. Create the conda environment from file
```shell
conda env create --file conda-env.yml
```
2. Activate environment 
```shell
conda activate cryptomemebot
```
3. Rename `config-dummy.py`to `config.py`, and add in all your Reddit and Telegram API details
5. Start cryptomemebot
```shell
python cryptomemebot.py
``` 
   
## ML chatbot
- Chatterbot (`chatterbot`) trained on the English corpus

## APIs used
- Reddit API (`praw`)
- Telegram API (`telegram` and `python-telegram-bot`)

### Exporting the conda environment
```shell
conda env export --no-builds | grep -v "^prefix: " > conda-env.yml
```
