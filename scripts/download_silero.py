"""Download the pinned German Silero model and verify its SHA-256 before loading."""
import hashlib
from pathlib import Path
import ssl
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MODEL_SHA256 = '2e22f38619e1d1da96d963bda5fab6d53843e8837438cb5a45dc376882b0354b'
MODEL_URLS = [
    'https://models.silero.ai/models/tts/de/v3_de.pt',
    'https://huggingface.co/maerkeov/silero-tts-de/resolve/main/v3_de.pt?download=true',
]


def verified(path):
    return path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == MODEL_SHA256


def download(destination=ROOT/'models/silero-v3-de.pt'):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if verified(destination):
        return destination
    partial = destination.with_suffix('.part')
    errors = []
    for url in MODEL_URLS:
        try:
            deadline = time.monotonic() + 60
            with urllib.request.urlopen(url, timeout=20, context=ssl.create_default_context()) as response, partial.open('wb') as output:
                while chunk := response.read(256*1024):
                    if time.monotonic() > deadline:
                        raise TimeoutError('Download exceeded 60 seconds; trying the pinned mirror.')
                    output.write(chunk)
            if not verified(partial):
                raise ValueError('Silero model checksum does not match.')
            partial.replace(destination)
            print(f'Verified Silero German model: {destination}', flush=True)
            return destination
        except Exception as error:
            errors.append(str(error))
            partial.unlink(missing_ok=True)
    raise RuntimeError('Could not download the German model: ' + '; '.join(errors))


if __name__ == '__main__':
    download()
