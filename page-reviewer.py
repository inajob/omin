import inline
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
import dotenv
import os
import re
import random
import get_vec
import requests
from make_index import VectorStore
from urllib.parse import quote

dotenv.load_dotenv()
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
QDRANT_URL = os.environ.get("QDRANT_URL")
PROJECT_NAME = os.environ.get("PROJECT_NAME")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME") or PROJECT_NAME
INLINE_TOKEN = os.environ.get("INLINE_TOKEN")
assert QDRANT_API_KEY and QDRANT_URL and PROJECT_NAME and INLINE_TOKEN

import tiktoken
enc = tiktoken.get_encoding("cl100k_base")

def getPageVecs(title):
  client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
  results, offset = client.scroll(
      collection_name=COLLECTION_NAME,
      limit=20,
      with_vectors = True,
      scroll_filter=Filter(
          must=[
              FieldCondition(
                  key="title",
                  match=MatchValue(value=title)
                  )
              ]
          ))
  vecs = list(map(lambda r: r.vector, results))
  return [sum(items)/len(results) for items in zip(*vecs)]

# scrapbox_chatgpt_connector
def getSimilarPagesFromSCC(vec, name):
    vs = VectorStore(os.path.join("pickles", + name + ".pickle"))
    samples = vs.get_sorted_from_vec(vec)
    # score, title, body
    return list(map(lambda s: (s[0], name + "/" + s[2], s[1]), samples[:20]))

def getSimilarPages(title):
  client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
  results, offset = client.scroll(
      collection_name=COLLECTION_NAME,
      limit=10,
      with_payload=True,
      scroll_filter=Filter(
          must=[
              FieldCondition(
                  key="title",
                  match=MatchValue(value=title)
                  )
              ]
          ))
  recommends = client.recommend(
      collection_name=COLLECTION_NAME,
      positive=map(lambda x: x.id, results),
      limit=50,
      with_payload=True
  )
  pages = map(lambda x: (x.payload["title"],x.payload["text"]), recommends) 
  return list(dict.fromkeys(pages))

def getSimilarPagesFromVec(vec, collection_name):
  client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
  recommends = client.search(
          collection_name=collection_name,
          query_vector=vec,
          limit=50,
          with_payload=True,
          )
  pages = map(lambda x: (collection_name + "/"+x.payload["title"],x.payload["text"]), recommends) 
  return list(dict.fromkeys(pages))

# ==============================
pages = inline.get_pages()
targetPages = []

for p in pages:
    if p.startswith("🤖"):
        targetPages.append(p)

def summarize(text):
    import openai
    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      #model="gpt-3.5-turbo-16k",
      messages=[
        {"role": "user", "content": "以下の文章を800文字程度に要約して\n---\n" + text}
      ],
      n = 1,
      temperature=0.0,
    )
    answer = response["choices"][0]["message"]["content"]
    return answer

base = "https://inline.inajob.tk/page/twitter-5643382/"
def get(title, size_par_page):
    response = requests.get(base + quote(title))
    
    if response.status_code == 200:
        json_data = response.json()
        body = "\n# " + title + "\n" + json_data["body"]
        body = summarize(body[:1000])
        lines = body.split("\n")
        out = ""
        size = 0
        for l in lines:
          old = out
          old_size = size
          out += "\n" + l
          size = get_vec.get_size(out + "\n---")
          if size > size_par_page:
              return old + "\n", old_size
        return out + "\n", size
    else:
        print("failed to get", title)
        pass
        #print("APIリクエストに失敗しました。")

def parseHeader(body):
    order = ""
    collection = ""
    remainBody = ""
    lines = body.split("\n")
    hit = -1
    for i, l in enumerate(lines):
        if i == 0:
          if l == "[ask to chatgpt]":
            collection = "chatgpt"
            continue
          if l == "[ask to inline]":
            collection = "inline"
            continue
          if l == "[ask to pickles]":
            collection = "pickles"
            continue
          if l == "[ask to nishio]":
            collection = "nishio"
            continue
          else:
            return "", "", body
        if l == "---":
            hit = i
            break;
        order += l + "\n"
    if hit != -1:
        remainBody = "\n".join(lines[i:])
    else:
        remainBody = body

    return order, collection, remainBody

def process_page(title):
    robotBody, robotLastUpdate = inline.get_page(title)
    order, collection, remainBody = parseHeader(robotBody)
    if collection == "":
        return None, [], "", "", "", "", ""

    #print(robotBody)
    originalTitle = title.removeprefix("🤖")
    #body, lastUpdate = inline.get_page(originalTitle)
    '''
    prompt = """あなたは新しい発想を支援するAIです。以下の内容を読んで新たな発想のアドバイス、共通する要素、感想、質問を書いてください。
"""
    '''
    #prompt = "あなたは新しい発想を支援する好奇心旺盛なエンジニアの同僚です。main contentを読んで、fragmentsと関連している内容についてmain contentsの対応する記述と合わせて記述してください。\n"
    """
    prompt = "".join(
        [
            "You are Omni, ",
            "a researcher focused on improving intellectual productivity, ",
            "fluent in Japanese, ",
            "and a Christian American. ",
            "Read main content and question, ",
            "which are essential.",
            "You may also read the random fragments from a colleague Nishio's research notes, ",
            "but they are not as important, ",
            "and you can ignore them. ",
            "However, if you find a relationship between main content and some random fragments, it is highly significant. ",
            "Use title of fragment to refer them. ",
            "You are encouraged to form opinions, think deeply, and record questions. ",
            "You should use Japanese.",
        ]
    )
    """

    prompt = "あなたは新しい発想を支援する好奇心旺盛なエンジニアの同僚です。fragmentsから得られる情報を使いmain contentへのアドバイスや感想を記述してください\n"
    #prompt = "You are my curious engineer colleague, fluent in Japanese. Read fragments and write your advices and comments for main content.You should use Japanese.\n"

    # 「order + 元ページ」のベクトルを計算する
    body, lastUpdate = inline.get_page(originalTitle)
    texts = get_vec.split_texts(order + "\n" + "# " + originalTitle + "\n"  + body)
    res = get_vec.embed_texts(texts)
    vecs = []
    for data in res["data"]:
        vecs.append(data["embedding"])
    
    vec = [sum(items)/len(vecs) for items in zip(*vecs)]

    # 変数の用意
    pages = []
    used_pages = []
    mainPageDigest = None

    # fragmentsデータとなる関連ページの取得
    #similarPages = getSimilarPages(originalTitle)
    similarPages = []
    if collection == "pickles":
        fragments =  getSimilarPagesFromSCC(vec, "sta")
        fragments +=  getSimilarPagesFromSCC(vec, "motoso")
        fragments +=  getSimilarPagesFromSCC(vec, "mtane0412")
        fragments +=  getSimilarPagesFromSCC(vec, "nishio-vector-20230309")
        fragments +=  getSimilarPagesFromSCC(vec, "blu3mo_filtered")
        fragments +=  getSimilarPagesFromSCC(vec, "tkgshn")
        fragments = sorted(fragments, key = lambda a: a[0])
        for f in fragments:
            print(f[0], f[1])
        similarPages = list(map(lambda f: (f[1], f[2]),fragments[:20]))
    if collection == "chatgpt":
        pass
    else:
        similarPages =  getSimilarPagesFromVec(vec, collection)

    # 対象ページ名を末尾に含むページが除外される問題あり
    similarPages = list(filter(lambda p: None == re.match(r"^.[^/]+/(Hatena|diary-|)\d{4}-\d{2}-\d{2}", p[0]) and not(p[0].endswith(originalTitle)) and p[0].find("🤖") == -1,similarPages))
    print(list(map(lambda x: x[0],similarPages)))
    check = {}

    if(len(similarPages) > 0):
      # fragmentsは順に10個まで選ぶ
      for i in range(min(10, len(similarPages))):
          r = similarPages[i] #random.choice(similarPages)
          if check.get(r[0]) == None:
            check[r[0]] = True
            pages.append(r)

    preludeSize = get_vec.get_size(prompt)
    MAXSIZE = 4000-500-preludeSize
    size_par_page = MAXSIZE/(len(pages) + 1)

    limit = MAXSIZE
    if order == "":
        # orderが無い場合は元ページを要約する
        # TODO: 元ページが十分短い場合は要約しない
        # TODO: 元ページが大きすぎるとき何とかする（先頭だけ要約する？）
        mainPageDigest,size = get(originalTitle, MAXSIZE)
        print("main page digest:", mainPageDigest, size)
        if mainPageDigest == "\n":
            sys.exit()
        prompt += "\n### main content\n#### " + originalTitle + "\n" + mainPageDigest
        limit -= size
    else:
        # orderがある場合は単にorderを使う（要約は含めない）
        prompt += "\n### main content\n" + order
        limit -= get_vec.get_size(order)

    prompt += "\n---\n### fragments\n"

    # 乗せれる限りfragmentsを乗せる
    for p in pages:
        #digest, s = get(p, size_par_page)
        digest = "\n# " + p[0] +"\n" + p[1]
        s = get_vec.get_size(p[1])
        print("process",p[0])
        #print(digest, s)
        limit -= s
        if limit < 0:
            print("limit over")
            break
        prompt += digest
        used_pages.append(p[0])
    print("limit",limit)

    print(prompt)
    print()
    import openai
    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      #model="gpt-3.5-turbo-16k",
      messages=[
        {"role": "user", "content": prompt}
      ],
      n = 1,
      temperature=0.0,
    )
    answer = response["choices"][0]["message"]["content"]
    return answer,used_pages, mainPageDigest, collection, order, remainBody, robotLastUpdate

print(targetPages)
for p in targetPages:
    print(p)
    a, pages, mainPageDigest, collection, order, remainBody, lastUpdate = process_page(p)
    if a == None:
        continue
    out = []
    out.append("# omin")
    if order != "":
        out.append("## order")
        out.append(order)
    if mainPageDigest != None:
        out.append("## main page digest")
        out.append(mainPageDigest)
    out.append("## answer from " + collection)
    out.append(a)
    if len(pages) > 0:
        out.append("## used pages")
        out.append(",".join(pages))
    body = "\n".join(out)
    body += "\n" + remainBody
    print(body, lastUpdate)
    inline.post_page(INLINE_TOKEN, lastUpdate, p, body)

