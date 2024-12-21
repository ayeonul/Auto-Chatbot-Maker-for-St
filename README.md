# 자동-완성 된 챗봇

> _시간 절약!_
> _멘탈도 깔끔_
> _**즐겁다**_
> _**마참내!**_

* 챗봇 엔진 자체의 설명은 [/chat_node.md](./chat_node.md)와 [/chatbot-with-bert.docx](/chatbot-with-bert.docx)를 참고해주세요.
* 여기선 챗봇 자동 생성에 대해서만 설명합니다.

## 사용법

> 이하 모든 설명은 `/.env` 파일의 내용이 제대로 입력되어있다는 전제를 가집니다.
> **시간이 좀 걸립니다.** 대화의도 7개 + greeting text + 웹사이트 9개 기준으로 약 8~13분 소요됩니다.
> **GPT 토큰도 꽤 많이 잡아먹어용**
> **gpt-4 이외 모델은 context length에 걸려 2개 이상의 웹사이트 데이터를 못 읽어요**

```python
from utils import ChatbotMaker

data = [
    {
        "code": "1",
        "title": "NCS란",
        "url": ["https://ncs.go.kr/th01/TH-102-001-01.scdo"],
    },
    {
        "code": "1.1",
        "title": "NCS 분류",
        "url": ["https://ncs.go.kr/th01/TH-102-001-02.scdo"],
    },
    {
        "code": "1.3",
        "title": "NCS 구성",
        "url": ["https://ncs.go.kr/th01/TH-102-001-03.scdo"],
    },
    {
        "code": "1.4",
        "title": "NCS 연혁",
        "url": ["https://ncs.go.kr/th01/TH-102-001-04.scdo"],
    },
    {
        "code": "2",
        "title": "NCS 학습모듈이란",
        "url": ["https://ncs.go.kr/th01/TH-102-002-01.scdo"],
    },
    {
        "code": "2.1",
        "title": "NCS 학습모듈의 구성",
        "url": [
            "https://ncs.go.kr/th01/TH-102-002-02.scdo",
            "https://ncs.go.kr/th01/TH-102-002-03.scdo",
            "https://ncs.go.kr/th01/TH-102-002-04.scdo",
        ],
    },
    {
        "code": "2.2",
        "title": "NCS 학습모듈의 활용",
        "url": ["https://ncs.go.kr/th01/TH-102-002-07.scdo"],
    },
]

greeting_text = "안녕하세요😊 저는 NCS 홈페이지 안내 챗봇이에요! NCS 홈페이지에 대해서 알려드릴게요! 궁금한 내용을 입력해주세요😉"

ChatbotMaker(
    model_name="gpt-4-1106-preview", chatbot_name="NCS 홈페이지 안내 챗봇", sitemap=data, greeting_text=greeting_text
)
```

`/utils.py`의 **ChatbotMaker** class에 **GPT 모델명**, **챗봇 이름**, 챗봇으로 만들 웹사이트의 **사이트맵 겸 챗봇 시나리오 구조**를 넣으면-**greeting text**는 선택사항이지만, 넣는 걸 권장합니다- `/예문.xlsx`에 챗봇의 예문이, `/chatbot-contents.json`에 챗봇 콘텐츠가 저장됩니다. 이 상태로 `README.md` 파일을 참고해 챗봇(혹은 API)을 구동하면 됩니다.

## 어떻게 동작하나요?

1. sitemap 변수의 각 코드의 유효성을 검사합니다.
   - 중복되는 게 있는지, 0이 아닌 int와 온점(.)으로만 구성되어 있는지 등을 검사합니다
2. chrome driver와 selenium을 이용, sitemap의 각 url들을 크롤링하여 **텍스트 데이터만을 수집합니다.** 이때, `<table>` 태그가 존재하면 그 태그 내의 내용만 markdown 문법으로 변환합니다. 수집된 텍스트 및 테이블 데이터들은 chatbot_contents(dict) 변수에 sitemap의 각 대화의도별로 저장됩니다.
3. 대화의도별 저장된 웹사이트의 데이터들을 GPT를 통해 500자 미만으로 요약합니다. 이때 greeting text가 있다면 그 말투나 분위기 등을 참고하며, 이 요약본이 챗봇이 대답할 안내문이 됩니다.
4. **챗봇이름**/**대화의도명**/**그 외 나머지 대화의도명**(예문 중복을 최소화하기 위함)과 GPT를 이용해 각 대화의도의 예문을 만들어냅니다.
5. `/예문.xlsx`와 `/chatbot-contents.json`으로 저장합니다! 이제 챗봇 내용 혹은 예문의 수정 및 `/README.md`의 내용을 따라 챗봇을 구동할 수 있습니다.

## 자동-완성 챗봇은 시각화 된 데모버전이 없나요?

> 라고 하셔서 streamlit으로 열심히 만들었습니다

```bash
cd backend
# 헐! conda 환경은 안 땄네요 근데 지금 쓰시는 환경들에 streamlit만 추가하세요
streamlit run app.py
```
