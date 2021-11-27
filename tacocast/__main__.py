import feedparser
import trafilatura

from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer
import pydub

import tenacity
import timeout_decorator

from environs import Env

import xml.etree.ElementTree as ET

import uuid
import os
import pathlib
from datetime import datetime

from .tqdm import tqdm
from .blockprint import blockprint
from .dynamic_window import dynamic_window

# TODO: Move all configurations under a proper yaml files
env = Env()
env.read_env(".env")
env.read_env(".env.default")

def to_speech(synthesizer, text, output_name):
    if pathlib.Path(output_name).exists():
        return

    lines = text.split('\n')

    # Tacotron has a tendancy to babble randomly/err vocalizingly. We retry if it takes more than 5 seconds, as it is likely that is what happened in that case
    @tenacity.retry(retry=tenacity.retry_if_exception_type(timeout_decorator.TimeoutError), stop=tenacity.stop_after_attempt(10))
    @timeout_decorator.timeout(env.int('MAX_TIME'))
    def synthesize(line):
        try:
            with blockprint(): # TTS outputs each and every line it synthetizes, which is not practical
                return synthesizer.tts(line)
        except RuntimeError:
            return []

    def split_line(line):
        # TODO:  explain
        result = [reversed(list(i)) for i in dynamic_window(reversed(synthesizer.seg.segment(line)), target=env.int('TARGET'), hard_target=env.int('HARD_TARGET'), key=len, inclusive=True)]
        result = [''.join(i) for i in reversed(result)]
        result = [(r + '.' if not r[-1] in '。，;:,” .?!)' else r) for r in result] # Add end punctuation. Tacotron has troubles reading titles otherwise
        
        return result
        
    synthesizer.save_wav([i for line in tqdm(lines, leave=True, postfix_func=lambda i: {'current': i[:50]}) for line_split in split_line(line) for i in synthesize(line_split)], output_name)

def extract_infos(url, **kwargs):
    downloaded = trafilatura.fetch_url(url)
    extract = trafilatura.bare_extraction(downloaded, url=url, include_comments=False)
    extract |= kwargs

    return extract

def __main__():
    ### Setup
    def read_etag(etag_file):
        try:
            with open(etag_file) as f:
                etag = f.read() or None
        except FileNotFoundError:
            etag = None
    
    feed = feedparser.parse(env('RSS_FEED'), etag=read_etag(env('ETAG_FILE')))

    def setup_synthesizer(models_json):
        manager = ModelManager(models_json)
        model_path, config_path, model_item = manager.download_model(env('DDC_MODEL'))
        vocoder_path, vocoder_config_path, _ = manager.download_model(env('VOCODER_MODEL') or model_item["default_vocoder"])

        synthesizer = Synthesizer(model_path, config_path, None, vocoder_path, vocoder_config_path, use_cuda=env.bool('USE_CUDA'))
        synthesizer.split_into_sentences = lambda i: [synthesizer.seg.cleaner(i).clean()]
        return synthesizer
    synthesizer = setup_synthesizer(env('MODELS_JSON'))

    out_tree = ET.ElementTree()
    out_tree.parse(env('FEED_OUTPUT_PATH'))
    out_tree_root = out_tree.find('.//channel')

    ### Main loop
    def create_audio_for_entry(synthesizer, extract):
        uid = extract.get('guid') or uuid.uuid4()
        wav_path = pathlib.Path('.') / env('OUTPUT_WAV_DIR') / f'{uid}.wav'
        path = pathlib.Path('.') / env('OUTPUT_WAV_DIR') / f'{uid}.mp3'

        if not path.exists():
            to_speech(synthesizer, extract['text'], wav_path)
            pydub.AudioSegment.from_wav(wav_path).export(path, format="mp3")
            os.remove(wav_path)

        return path

    def create_item_from_entry(entry, wavpath):
        result = ET.Element('item')

        def copy_tag(entry, tag):
            try:
                if isinstance(entry[tag], dict):
                    ET.SubElement(result, tag, entry[tag])
                else:
                    ET.SubElement(result, tag).text = str(entry[tag])
            except KeyError:
                pass
        [copy_tag(entry, i) for i in ('title', 'description', 'link', 'comments', 'pubDate')]
        
        ET.SubElement(result, 'enclosure', {'length': str(os.path.getsize(wavpath)), 'type': 'audio/wav', 'url': f'{env("BASE_URL")}{wavpath.name}'})
        ET.SubElement(result, 'pubDate').text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
        return result

    def create_item(synthesizer, entry):
        extract = extract_infos(entry['link']) 
        extract = extract | entry | {'guid': entry.get('guid'), 'title': extract['title']}
        path = create_audio_for_entry(synthesizer, extract)
        return create_item_from_entry(extract, path)

    to_append = [create_item(synthesizer, entry) for entry in tqdm(list(reversed(feed.entries)), postfix_func=lambda d: {k: d[k] for k in ['link']})]

    index = next(ix for ix, v in enumerate(out_tree_root) if v == out_tree.find('.//comment'))
    [out_tree_root.insert(index+1, i) for i in to_append]
    ET.indent(out_tree)
    out_tree.write(env('FEED_OUTPUT_PATH'))

    # Update etag now that we're done
    with open(env('ETAG_FILE'), 'w') as f:
        f.write(feed.etag)

if __name__ == '__main__':
    __main__()