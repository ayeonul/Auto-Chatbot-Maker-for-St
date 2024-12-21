import json
import pandas as pd
import numpy as np
from GPT import ChatGPT
import time
from dotenv import load_dotenv
import os, json
from tqdm.auto import tqdm

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


class ChatbotData:
    def __init__(self, encoder) -> None:
        with open("./chatbot-contents.json", "r", encoding="utf-8") as f:
            self.chatbot_contents = json.load(f)

        example_sen = pd.read_excel("./예문.xlsx", dtype={"code": str})
        # example_sen.columns = ["sentence", "code"]
        # example_sen = example_sen.astype({"code": str})
        # example_sen =  []
        # for data in self.chatbot_contents:
        #     text = data.get("contents", [])[0].get("text", "")
        #     text = re.sub(r'\n+', '\n',text)
        #     text = text.replace('.', '.\n')
        #     text = [s for t in text.split("\n") if (s := t.strip())]
        #     example_sen.append({"sentence": text, "code": data.get("code")})

        # example_sen = pd.DataFrame(example_sen)
        example_sen["parents"] = example_sen["code"].apply(self.__split_last_part)
        example_sen["sentence"] = example_sen["sentence"].str.upper()

        sen_emb = []
        for _, data in example_sen.iterrows():
            emb = encoder([data["sentence"]]).mean(axis=0, keepdims=True)
            sen_emb.append(
                {"emb": emb, "code": data["code"], "parents": data["parents"]}
            )

        df_sen_emb = pd.DataFrame(sen_emb)

        mean_dict = {
            code: np.nanmean(np.stack(group["emb"].values, axis=0), axis=0)
            for code, group in df_sen_emb.groupby("code")
        }

        for code, mean in mean_dict.items():
            parts = code.split(".")
            if len(parts) > 1:
                for depth in range(len(parts) - 1, 0, -1):
                    parent_code = ".".join(parts[:depth])
                    mean_dict[code] = (mean_dict.get(parent_code, 0) + mean) / 2

        hir_mean_embs = []

        for _, data in df_sen_emb.iterrows():
            if (p_code := data["parents"]) is None:
                hir_mean_embs.append(data["emb"])

            else:
                hir_mean_embs.append((mean_dict[p_code] + data["emb"]) / 2)

        self.example_embs = df_sen_emb[["code"]].copy()
        self.example_embs["emb"] = hir_mean_embs

    @staticmethod
    def __split_last_part(code):
        parts = code.rsplit(".", 1)
        if len(parts) != 1:
            return parts[0]


class ChatbotEngine:
    def __init__(self, encoder, engine, contents) -> None:
        self.encoder = encoder
        self.engine = engine
        self.contents = contents

    def find_chat_contents(self, code):
        return next(
            (item for item in self.contents if item["code"] == code),
            {},
        )

    async def chat(
        self,
        user_input,
        MAX_INFERENCE_BOUND,
        MIN_INFERENCE_BOUND,
        FALLBACK_TEXT,
        MULTI_INTENTS_TEXT,
        ERROR_TEXT,
        queue=None,
    ):
        user_emb = self.encoder([user_input.upper()]).mean(axis=0, keepdims=True)
        search_res_df = self.engine.search(user_emb, n=5)
        search_res_df = search_res_df.drop_duplicates(["code"]).astype({"code": str})
        first_res = search_res_df.iloc[0]
        # print(first_res["score"])

        if first_res["score"] >= MAX_INFERENCE_BOUND:
            res_content = self.find_chat_contents(first_res["code"])
            if res_content == {}:
                res_content = {
                    "code": "error",
                    "title": "error",
                    "contents": [
                        {
                            "type": "speak",
                            "image": None,
                            "text": ERROR_TEXT,
                            "button": [],
                        }
                    ],
                }
            return res_content

        elif (
            MIN_INFERENCE_BOUND < first_res["score"]
            and first_res["score"] < MAX_INFERENCE_BOUND
        ):
            multi_intent_res = {
                "code": "multi-intents",
                "title": "multi-intents",
                "contents": [
                    {
                        "type": "speak",
                        "image": None,
                        "text": MULTI_INTENTS_TEXT,
                        "button": [
                            {
                                "text": self.find_chat_contents(data["code"]).get(
                                    "title"
                                ),
                                "type": "call_flow",
                                "action": data["code"],
                            }
                            for _, data in search_res_df.iterrows()
                            if MIN_INFERENCE_BOUND < data["score"]
                        ],
                    }
                ],
            }
            return multi_intent_res

        else:
            if queue is not None:
                await queue.put(user_input)
            fallback_res = {
                "code": "fallback",
                "title": "fallback",
                "contents": [
                    {
                        "type": "speak",
                        "image": None,
                        "text": FALLBACK_TEXT,
                        "button": [],
                    }
                ],
            }
            return fallback_res


class ChatbotMaker:
    def __init__(
        self,
        model_name: str,
        chatbot_name: str,
        sitemap: list,
        greeting_text: str = None,
    ) -> None:
        """
        sitemap = [
            {
                "code": "1",
                "title": "학과소개",
                "url": [
                    "http://computer.bist.ac.kr/contents/contents_view.php?site_id=computer&TREE_NO=1656&DEPTH=3",
                    "http://computer.bist.ac.kr/contents/contents_view.php?site_id=computer&TREE_NO=1657&DEPTH=3",
                ],
            },
            {
                "code": "1.1",
                "title": "교수소개",
                "url": [
                    "http://computer.bist.ac.kr/professor/list.php?site_id=computer&TREE_NO=1579&DEPTH=2"
                ],
            },
            {
                "code": "1.2",
                "title": "교육과정",
                "url": [
                    "http://computer.bist.ac.kr/contents/contents_view.php?site_id=computer&TREE_NO=1658&DEPTH=3",
                    "http://computer.bist.ac.kr/contents/contents_view.php?site_id=computer&TREE_NO=1660&DEPTH=3",
                    "http://computer.bist.ac.kr/contents/contents_view.php?site_id=computer&TREE_NO=1664&DEPTH=3",
                    "http://computer.bist.ac.kr/contents/contents_view.php?site_id=computer&TREE_NO=1666&DEPTH=3",
                ],
            },
            {
                "code": "1.3",
                "title": "학과시설",
                "url": [
                    "http://computer.bist.ac.kr/contents/contents_view.php?site_id=computer&TREE_NO=1582&DEPTH=2"
                ],
            },
        ]"""
        load_dotenv(override=True)

        codes = [item["code"] for item in sitemap]
        is_duplicate = []
        is_valid = []

        # 각 "code"에 대해 검사 수행
        for code in codes:
            is_duplicate.append(codes.count(code) > 1)
            is_valid.append(self.__is_valid_code(code))

        if any(is_duplicate) or not all(is_valid):
            raise ValueError(
                "sitemap의 각 code값 중 이상한 게 있습니다. 각 code값은 0이 들어가선 안 되며, n.n.n의 방식이어야 합니다. 서로 중복되어서도 안 되고, 끝자리가 온점(.)이어서도 안 됩니다"
            )

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        # 각 URL에 대해 텍스트와 테이블 데이터 추출
        for item in tqdm(sitemap):
            for url in item.get("url", []):
                if isinstance(url, str) and len(url) != 0:
                    combined_text = self.extract_text_with_tables(driver, url)
                    if d := item.get("data"):
                        d.append(combined_text)
                    else:
                        item["data"] = [combined_text]

        # WebDriver 종료
        driver.quit()
        creater_concept = f"""\
        You are a chatbot designed to summarize the contents of a provided web page (or pages) into an answer for another chatbot in 500 characters or less. Unless specifically requested, you should respond only in Korean. Do not use greetings like "안녕하세요", "어서오세요", "안녕!" in your summary. Also, avoid including phrases that indicate quoting from a homepage, such as "This page shows~".\
        """
        creater = ChatGPT(os.getenv("OPENAI_KEY"), model_name, creater_concept)

        chatbot_contents = []
        titles = []
        for item in tqdm(sitemap):
            titles.append(item.get("title"))

            content = {
                "code": item.get("code"),
                "title": item.get("title"),
                "contents": [
                    {"type": "speak", "image": None, "text": "", "button": []}
                ],
            }
            if len((urls := item.get("url", []))) > 0:
                content["contents"][0]["button"] = [
                    {"text": "더 알아보기", "type": "url", "action": urls[0]},
                ]
            if (raw_data := item.get("data")) is not None:
                web_text = "\n".join(raw_data)
                if greeting_text is not None:
                    prompt = f"""Below is the {item.get('title')} for {chatbot_name}. web page (or pages) contents.

{web_text}
---
Summarize the content regardless of the tone of the text on the web page, but match the tone, personality, formal or informal speech, and atmosphere of the greeting provided below. Below are the greetings to refer to for the tone of the web page summary:
{greeting_text}"""
                else:
                    prompt = f"""Below is the {item.get('title')} for {chatbot_name}. web page (or pages) contents.

{web_text}
---
Regardless of the content of the webpage, provide the summary in a polite tone like a information chatbot.
"""
                gpt_res = creater([{"role": "user", "content": prompt}])
                content["contents"][0]["text"] = gpt_res["res"][0]["res"]

            chatbot_contents.append(content)

            time.sleep(3)

        if greeting_text is not None:
            chatbot_contents = [
                {
                    "code": "0",
                    "title": "인사말(main)",
                    "contents": [
                        {
                            "type": "speak",
                            "image": None,
                            "text": greeting_text,
                            "button": [],
                        }
                    ],
                }
            ] + chatbot_contents

        example_concept = """\
You are a bot that creates example sentences for each conversation intent for making chatbots. Upon receiving information about each conversation intent, return 10 Korean user example sentences of varying lengths related to the title of that conversation intent. Each example must be separated by a slash (/). Some of the examples must necessarily be words or a list of words, not sentences. These examples should not resemble those of other conversation intents, so use the provided "other intent names" to predict examples of other intents and compose ones that differ as much as possible from them.
"""
        example_chat = ChatGPT(
            os.getenv("OPENAI_KEY"),
            model_name,
            example_concept,
            temperature=0.82,
        )

        example_sentences = []

        for contents in tqdm(chatbot_contents):
            if (code := contents.get("code")) is not None:
                if code == "0":
                    sentences = [
                        "안녕",
                        "안녕하세요",
                        "ㅎㅇ",
                        "하이염",
                        "첫페이지",
                        "처음으로",
                        "인사",
                        "처음",
                        chatbot_name,
                    ]
                    example_sentences += [
                        {"sentence": sen, "code": code} for sen in sentences
                    ]
                    continue

                example_sentences += [{"sentence": contents.get("title"), "code": code}]
                if len(contents.get("contents", [{}])[0].get("text", "")) != 0:
                    prompt = f"chatbot name: {chatbot_name}\nintent title: {contents.get('title')}\nother intent names:{'/'.join([title for title in titles if title != contents.get('title')])}"

                    dialog = [
                        {
                            "role": "user",
                            "content": "chatbot name: 카카오프렌즈샵 챗봇\nintent title: 카카오프렌즈샵 안내\nother intent names: 카카오프렌즈샵 판매 목록/카카오프렌즈샵 콜라보 제안/카카오프렌즈샵 역사/카카오프렌즈샵 이벤트 정보",
                        },
                        {
                            "role": "assistant",
                            "content": "카카오프렌즈샵이 뭔가요?/카카오프렌즈샵은 어디에 있나요?/카카오프렌즈샵이 뭐임?/카카오샵/카카오프렌즈샵 알려줘/프렌즈샵 어딨음?/카카오샵 위치좀/프렌즈샵",
                        },
                        {"role": "user", "content": prompt},
                    ]
                    chat_res = example_chat(dialog)
                    try:
                        sentences = chat_res["res"][0]["res"].split("/")
                    except:
                        continue
                    else:
                        example_sentences += [
                            {"sentence": sen, "code": code}
                            for sen in sentences
                            if sen.strip()
                        ]
                time.sleep(3)

        with open("chatbot-contents.json", "w", encoding="utf-8") as f:
            json.dump(chatbot_contents, f, ensure_ascii=False, indent=2)
        sentence_df = pd.DataFrame(example_sentences)
        sentence_df.to_excel("./예문.xlsx", index=None)

        print("All done!")

    @staticmethod
    def extract_text_with_tables(driver, url):
        full_text = ""
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*"))
            )
        except TimeoutException:
            return ""

            # 페이지의 모든 요소 순회하며 텍스트와 테이블 추출
        elements = driver.find_elements(By.XPATH, "//*")
        for element in elements:
            if element.tag_name == "table":
                # 테이블을 Markdown으로 변환
                table_html = element.get_attribute("outerHTML")
                df = pd.read_html(table_html)[0]
                full_text += df.to_markdown() + "\n\n"
            elif element.text.strip():
                full_text += element.text + "\n\n"

        return full_text

    @staticmethod
    def __is_valid_code(code):
        # 온점으로 분할
        parts = code.split(".")
        # 마지막 문자가 온점인지, 각 부분이 숫자이며 0이 아닌지 확인
        return (code[-1] != ".") and all(
            part.isdigit() and int(part) != 0 for part in parts
        )
