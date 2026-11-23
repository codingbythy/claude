import sys, json, subprocess, soundfile as sf
from faster_whisper import WhisperModel
n = sys.argv[1]
subprocess.run(f"ffmpeg -y -loglevel error -i el/vo{n}.mp3 -ar 16000 -ac 1 el/v16_{n}.wav", shell=True, check=True)
m = WhisperModel('small.en', device='cpu', compute_type='int8')
a, _ = sf.read(f'el/v16_{n}.wav', dtype='float32'); seg, _ = m.transcribe(a, word_timestamps=True)
w = [(x.word.strip(), round(float(x.start), 2), round(float(x.end), 2)) for s in seg for x in s.words]
json.dump(w, open(f'el/words{n}.json', 'w')); print(len(w)); print(' '.join(x[0] for x in w))
