# Waffle Bot

This is a bot that I made, named after my dog, for servers that I like.

## Current Features

- Full Moderation Commands
- Persistent Mute Role
- Moderation Logs
- Reputation System
- Support for PostgreSQL

## Installation

I would prefer that you don't run an instance of my bot, but for learning purposes I have included instructions
on how to set it up regardless.

### Prerequisites
- Have a PostgreSQL database
- Create a Discord Bot application

### Setup
1. First install the requirements using pipenv
```
pipenv install
```

2. Then, to generate a settings.cfg file, you will need to run the bot for the first time.
I have included a script in pipenv that will do this, so just run
```
pipenv run start
```

3. Once you have generated the config file you will need to fill in the details, in the settings.cfg
file you will need to provide you bot token, and the URL to your PostgreSQL database.

Then, you should be able to run the bot again using the `pipenv run start` script and it should work.
