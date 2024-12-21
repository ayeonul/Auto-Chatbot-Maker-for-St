import streamlit as st

from engine.search import Search
from engine.encoder import Encoder
from utils import *
from dotenv import load_dotenv
import os, asyncio

# 초기 세션 상태 설정
if "data" not in st.session_state:
    st.session_state.data = [
        {"code": "", "title": "", "url": ["", "", "", ""], "delete": False}
    ]
if "bot_name" not in st.session_state:
    st.session_state.bot_name = ""
if "use_greeting" not in st.session_state:
    st.session_state.use_greeting = False
if "greeting_text" not in st.session_state:
    st.session_state.greeting_text = ""
if "chatbot_opt" not in st.session_state:
    load_dotenv()
    st.session_state.chatbot_opt = {
        "OPENAI_KEY": os.getenv("OPENAI_KEY"),
        "MIN_INFERENCE_BOUND": float(os.getenv("MIN_INFERENCE_BOUND")),
        "MAX_INFERENCE_BOUND": float(os.getenv("MAX_INFERENCE_BOUND")),
        "PORT": int(os.getenv("PORT")),
        "MULTI_INTENTS_TEXT": os.getenv("MULTI_INTENTS_TEXT"),
        "FALLBACK_TEXT": os.getenv("FALLBACK_TEXT"),
        "ERROR_TEXT": os.getenv("ERROR_TEXT"),
    }
if "encoder" not in st.session_state:
    st.session_state.encoder = Encoder()
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("자동-완성된 챗봇")

# 챗봇 이름 입력
st.text_input("챗봇 이름", key="bot_name")

# 인사말 사용 여부 체크박스
use_greeting = st.checkbox("인사말 사용", value=st.session_state.use_greeting)

# 인사말 텍스트 에어리어 (체크박스가 선택된 경우에만 표시)
if use_greeting:
    greeting_text = st.text_area("인사말", value=st.session_state.greeting_text)

# '추가' 버튼
if st.button("데이터 추가"):
    st.session_state.data.append(
        {"code": "", "title": "", "url": ["", "", "", ""], "delete": False}
    )

# 각 데이터 항목에 대한 폼
for i, item in enumerate(st.session_state.data):
    with st.container():
        cols = st.columns([1, 3, 1])
        with cols[0]:
            item["code"] = st.text_input(f"코드", item["code"], key=f"code{i}")
        with cols[1]:
            item["title"] = st.text_input(f"제목", item["title"], key=f"title{i}")
        with cols[2]:
            item["delete"] = st.checkbox("삭제", key=f"delete{i}")

        # URL 입력 필드 (고정된 길이 4)
        for j in range(4):
            item["url"][j] = st.text_input(
                f"URL {j+1}",
                item["url"][j] if j < len(item["url"]) else "",
                key=f"url{i}_{j}",
            )
        st.divider()

# 폼 제출 버튼
submitted = st.button("챗봇 생성")
if submitted:
    # 삭제 표시된 데이터 제거
    st.session_state.data = [
        item for item in st.session_state.data if not item["delete"]
    ]
    # 인사말 사용 여부 및 텍스트 업데이트
    st.session_state.use_greeting = use_greeting
    if use_greeting:
        st.session_state.greeting_text = greeting_text
    st.write("챗봇 이름:", st.session_state.bot_name)
    st.write("인사말 사용 여부:", "사용함" if st.session_state.use_greeting else "사용 안 함")
    st.write(
        "인사말:",
        st.session_state.greeting_text if st.session_state.use_greeting else "N/A",
    )

    with st.spinner('잠시만 기다려 주세요...'):
        ChatbotMaker(
            model_name="gpt-4-1106-preview",
            chatbot_name=st.session_state.bot_name,
            sitemap=st.session_state.data,
            greeting_text=greeting_text if use_greeting else None,
        )

chatbot_data = ChatbotData(st.session_state.encoder)
engine = Search(chatbot_data.example_embs[["emb"]], chatbot_data.example_embs[["code"]])

chatbot_engine = ChatbotEngine(
    st.session_state.encoder, engine, chatbot_data.chatbot_contents
)


async def async_chat(user_input):
    response = await chatbot_engine.chat(
        user_input,
        st.session_state.chatbot_opt["MAX_INFERENCE_BOUND"],
        st.session_state.chatbot_opt["MIN_INFERENCE_BOUND"],
        st.session_state.chatbot_opt["FALLBACK_TEXT"],
        st.session_state.chatbot_opt["MULTI_INTENTS_TEXT"],
        st.session_state.chatbot_opt["ERROR_TEXT"],
    )
    return response


def run_chat(user_input):
    return asyncio.run(async_chat(user_input))

# greeting_res = chatbot_engine.find_chat_contents('0')
# st.session_state.messages.append({"role": "assistant", "content": greeting_res.get("contents", "")[0]["text"]})

st.divider()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        response = run_chat(prompt)

        assistant = response.get("contents", "")[0]["text"]

        message_placeholder.markdown(assistant)
    st.session_state.messages.append({"role": "assistant", "content": assistant})
