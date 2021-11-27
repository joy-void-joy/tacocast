# tacocast

Convert your RSS feed into a podcast
This is a wrapper around [TTS](https://github.com/mozilla/TTS) to automatically add it to rss feeds

## How to use
```
git clone https://github.com/joy-void-joy/tacocast
cd tacocast
```
Create your own virtual environment. Then:
```
pip install -r requirements.txt
```
You will need to input your own values in .env if you want to use it on your own RSS feed. Otherwise, just add entries to in_feed.xml
```
python -m tacocast
```

Resulting files will be in output (you can also change .env to automatically push to your server)

## Workflow
My own workflow is to host a feed.xml file derived from in_feed.xml on my server. I use [Freshrss](https://freshrss.github.io/FreshRSS/en) on that file so that I can also aggregate other RSS feeds.
I then use [bindfiles](https://github.com/joy-void-joy/bindfiles) to edit this feed.xml whenever I need to add something
For tacocast, I use cron/manual runs, and have an sshfs to output them directly on my server

## Todo
[ ] add better comments/file separation
[ ] remove tqdm.py and convert it into a PR to tqdm
[ ] remove .env and convert it to a proper yaml configuration
