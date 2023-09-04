import openai
import tiktoken
import dotenv
import os
import re
import time
DEFAULT_BLOCK_SIZE = 500

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
enc = tiktoken.get_encoding("cl100k_base")

def get_size(text):
    "take text, return number of tokens"
    return len(enc.encode(text))

def clean(line):
    line = line.strip()
    # line = re.sub(r"https?://[^\s]+", "URL", line)
    line = re.sub(r"[\s]+", " ", line)
    return line

# DEFAULT_BLOCK_SIZEより大きなtextを分割する、分割時はのりしろを付ける
# のりしろ不要では？
def split_texts(input):
  lines = input.split("\n")
  block_size=DEFAULT_BLOCK_SIZE
  
  buf = []
  texts = []
  for line in lines:
      buf.append(line)
      body = clean(" ".join(buf))
      if get_size(body) > block_size:
          texts.append("\n".join(buf))
          buf = buf[len(buf) // 2 :] # 半分より上を削る
  body = clean(" ".join(buf))
  if body:
      texts.append("\n".join(buf))
  
  return texts

def embed_texts(texts, sleep_after_sucess=1):
    EMBED_MAX_SIZE = 8150  # actual limit is 8191
    if isinstance(texts, str):
        texts = [texts]
    for i, text in enumerate(texts):
        text = text.replace("\n", " ")
        tokens = enc.encode(text)
        # tokenが長すぎる場合は後ろは捨てる
        if len(tokens) > EMBED_MAX_SIZE:
            text = enc.decode(tokens[:EMBED_MAX_SIZE])
        texts[i] = text

    count = 0
    while True and count < 5:
        count += 1
        try:
            res = openai.Embedding.create(input=texts, model="text-embedding-ada-002")
            time.sleep(sleep_after_sucess)
        except Exception as e:
            print(e)
            time.sleep(1)
            continue
        break

    return res


if __name__ == "__main__":
    texts = split_texts("""- AIと箇条書き情報をやり取りする
      - 元となる箇条書きのベクトルを取りだしてQdrantに問い合わせるようにしたい
    """)
    res = embed_texts(texts);
    print(res)
