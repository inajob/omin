import requests
import os
from urllib.parse import quote

base = "https://inline.inajob.tk/page/twitter-5643382/"
def get_page(title):
    response = requests.get(base + quote(title))
    if response.status_code == 200:
        json_data = response.json()
        body = json_data["body"]
        lastUpdate = json_data["meta"]["lastUpdate"]
        return body, lastUpdate
    else:
        print("failed to get " + title)
        pass
        #print("APIリクエストに失敗しました。")

def prepend_page(token, title, text):
    body, lastUpdate = get_page(title)
    return post_page(token, lastUpdate, title, text + "\n" + body)

def post_page(token, lastUpdate, title, body):
    data = {
            "lastUpdate": lastUpdate,
            "body": body 
            }
    headers = {
            "User": token,
            }
    response = requests.post(base + quote(title), data, headers=headers)
    if response.status_code == 200:
        return True
    else:
        print(response)
        print("failed to post " + title)
        return False


def get_pages():
    response = requests.get(base)
    
    if response.status_code == 200:
        json_data = response.json()
        keywords = json_data["keywords"]
        return keywords

if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()
    INLINE_TOKEN = os.environ.get("INLINE_TOKEN")
    prepend_page(INLINE_TOKEN, "bot-test", "hello from script")
