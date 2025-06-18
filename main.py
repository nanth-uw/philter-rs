from pathlib import Path

from tqdm import tqdm

from philter_rs import PhilterEngine

engine = PhilterEngine()
r = engine.process("Hi my name is Nick Anthony! I was born on 9/9/95.")
print(r)

texts = []
example_files = list((Path().cwd() / "data" / "i2b2_examples").glob("*txt"))
for fpath in example_files:
    with open(fpath, "r") as f:
        texts.append(f.read().strip())

for text in tqdm(texts * 100):
    r = engine.process(text)
    # print(r)
