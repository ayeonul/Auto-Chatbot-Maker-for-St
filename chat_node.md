# chatbot-with-bert

> 단비 챗봇을 대신할 무언가... **BERT를 이용해서 만든 챗봇**입니다.
> 샘플로 들어간 내용들은 부산과기대 컴퓨터과 챗봇 중 일부입니다

샘플 데이터를 변경하고 싶다면, `chatbot-contents.json` 파일의 양식에 맞춰 _챗봇 발화문_(단비에선 *대화 흐름*으로 명명, 이하 _대화흐름_)을 작성합니당.
이후 `/예문.xlsx` 파일에 대화흐름별 예문|대화흐름 코드(후술) 순으로 작성합니다. _대화흐름 코드에 혼동이 없도록 주의합시다._
*현재 front는 carousel 형식과 speak(단순답변) 형식만 구현*되어 있는데 사실 기 챗봇도 이 두 가지 node만 사용하다시피 하니 큰 문제는 없을 것 같습니당. 새로운 타입의 node를 구현하고 싶다면 대충 지어서 추가 후 front에서 구현 방법을 추가하면 됩니다...

파일 구조가 꽤 복잡하니 작성 시엔 depth와 key 값들에 주의합시다.

- `/chatbot-contents.json` 파일은 object(dict)로 이루어진 array(list)입니다. 각 요소(object)들의 key는 다음을 나타냅니다:
  - `code`(str): _대화흐름 코드. string!!!!!!_ 예문 파일에 작성할 대화흐름 코드가 이쪽입니다.   중복만 없다면 어떤 방식으로-숫자가 아니어도 좋습니다- 작성해도 좋으나, 샘플 파일엔 기 단비 챗봇들과 동일하게 _{1 depth}.{2 depth}.{3 depth}..._ 식으로 해놓았습니다.
  - `title`(str): _대화흐름명._ 중의적인 의도(multi-intents, 이런 의미인가요?) 응답에서 나타나는 버튼에서도 표시될 이름입니다.
  - `contents`(array): _챗봇이 응답할 내용._ 각 컨텐츠를 화면에 표시될 순서대로, object로 집어넣으면 됩니다.예컨대, carousel-speak 대화흐름이라면 carousel 컨텐츠를 넣고, speak 컨텐츠를 넣으면 됩니다. 아래는 node 타입별로 내용이 달라집니다#### speak node

    _speak_ type은 일반 대화처럼 대답하는 형식입니다. 이미지나 버튼을 추가할 수도 있고, 그냥 텍스트만 || 이미지만 || 버튼만 대답할 수도 있구요. 카드형은 후술할 _carousel_ 타입에서 다룹니다.

    - `type`(str): _speak_ or _carousel_. 여기선 _speak_ type을 설명합니다.
    - `image`(str||null): _이미지 파일명._ 지금 구현된 front에선 `/src/assets/img/`에 있는 이 `image`값을 찾아 화면에 띄우도록 되어있는데, 이후 실사용 시엔 클라우드 등에 이미지를 업로드한 뒤 `<img src="...">` 등으로 띄울 듯 싶어용. 표시할 이미지가 없으면 *null*값을 넣읍시당
    - `text`(str||null): _표시할 텍스트_. 필요 없다면 *null*값을 넣읍시당
    - `button`(array)`: _표시할 버튼._ obj로 이루어진 array입니다. 버튼을 표시하지 않고 싶다면 빈 array만을 넣으세요.
      - `text`(str): _버튼에 표시될 텍스트_
      - `type`(str): _버튼 액션 type_, *call_flow(타 대화흐름 호출)* or _url(새 창으로 url 오픈)_. 현재 front에선 이 두 타입만 구현되어 있는데, 이 역시 새로운 타입의 버튼을 구현하고 싶다면 이름 대충 지어서 추가 후 front에서 구현 방법을 추가하면 됩니다.
      - `action`(str): _버튼이 액션을 취할 대상_. 위의 button type와 짝을 이루어야 합니다. 예컨대 call_flow(타 대화흐름 호출)이라면 다른 대화흐름의 code, url(새 창으로 url 오픈)이라면 오픈할 url이어야겠죵

    #### carousel node

    _carousel_ type은 카드형 답변입니다. 이미지와 버튼을 추가할 수 있으며, 사실상 _speak_ type이 여러개 있는 형태입니다.- `type`(str): _speak_ or _carousel_. 여기선 _carousel_ type을 설명합니다.


    - `content`(array): _carousel 콘텐츠._ `image`, `text`, `button`으로 이뤄진 obj로 구성된 array이며, 위 _speak_ 노드와 내용이 같습니다

API는 `/main.py`에 `uvicorn`+`FastAPI`로 작성되어 있습니다.

- `/api/chat-engine`: _사용자 입력을 받아 임베딩 > 예문의 임베딩과 유사도 비교 > 유사도가 제일 높은 예문과 짝을 이루는 대화흐름 반환_ 의 과정을 거쳐 대화흐름를 반환합니다.만일 유사도가 `.env`의 `MIN_INFERENCE_BOUND` 값과 `MAX_INFERENCE_BOUND` 사이라면 multi-intent 응답을 보내고, 그 이하라면 fallback을 반환합니다.
- `/api/gpt-chat-engine`: *첫 의도 추론 실패 시 재추론에 GPT의 function call을 사용*하는 method. `/api/chat-engine`과 같은 절차를 밟은 뒤 fallback이 발생하면 OpenAI GPT API를 이용해 사용자 발화를 요약, 이를 이용해 의도를 재추론합니다.
- `/api/call-flow`: *대화흐름 호출 method*. *call_flow* 버튼, *챗봇 시작 시 greeting*을 호출하기 위해 쓰는 API. 대화흐름 code를 주면 그에 맞는 대화흐름을 반환해줍니다.
