# FDC-Monitoring Agentic RAG — MVP

**목표**: `data/manuals/*.md` 5종을 단일 vectorstore에 넣고, LLM agent가 `retrieve_manual_knowledge` 툴을 통해 근거를 인용하며 답변하는 최소 구현.

**이번 노트북에서 다루지 않는 것** (의도적으로 단순화):
- BM25 / reranker / NLI judge
- 전체 evaluation 자동 채점
- 7단계 guardrail
- Streamlit UI
- 복잡한 src 모듈 분리

**흐름**
1. `.env` 로드 + API 키 검증
2. `data/manuals/*.md` 로드
3. `section_id` 기준 chunk 생성 (정규식 `## SECTION-ID | title` 또는 `### SECTION-ID | title`)
4. 각 chunk에 `file_name / section_id / title / citation` metadata 부착
5. `OpenAIEmbeddings(text-embedding-3-small)` + FAISS
6. retriever 생성
7. `retrieve_manual_knowledge(query)` tool 정의 — 인용 라벨 자동 포함
8. `ChatOpenAI` + `create_agent`
9. `data/voc/voc_samples.json`에서 difficulty 분산된 8건 골라 실행

## 0. (필요 시) 의존성 설치

이미 설치되어 있다면 건너뛰세요.


```python
# %pip install -q langchain langchain-openai langchain-community langchain-text-splitters faiss-cpu python-dotenv
```

## 1. 환경 변수(.env) 로드 + API 검증

프로젝트 루트의 `.env` 안에 다음 키가 있다고 가정합니다.
- `OPENAI_API_KEY` (필수)
- `LANGSMITH_API_KEY` (선택 — 있으면 트레이싱 활성화)

검증 순서:
1. dotenv 로드 → 환경변수 적용
2. 키 존재 여부 print
3. OpenAI 호출 1회로 실제 연결 확인


```python
import os
from pathlib import Path
from dotenv import load_dotenv

# notebooks/ 에서 실행해도 프로젝트 루트의 .env를 찾도록 상위 경로까지 탐색
PROJECT_ROOT = Path.cwd()
if PROJECT_ROOT.name == "notebooks":
    PROJECT_ROOT = PROJECT_ROOT.parent

env_path = PROJECT_ROOT / ".env"
loaded = load_dotenv(dotenv_path=env_path, override=True)
print(f".env 로드: {loaded}  (경로: {env_path})")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

def _mask(k):
    if not k:
        return "(없음)"
    return k[:6] + "..." + k[-4:] if len(k) > 12 else "***"

print(f"OPENAI_API_KEY    : {_mask(OPENAI_API_KEY)}")
print(f"LANGSMITH_API_KEY : {_mask(LANGSMITH_API_KEY)}")

assert OPENAI_API_KEY, "OPENAI_API_KEY 가 .env 에 없습니다."

# LangSmith 활성화 (선택)
if LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    os.environ.setdefault("LANGCHAIN_PROJECT", "fdc-monitoring-mvp")
    print("LangSmith tracing 활성화 — project=fdc-monitoring-mvp")
else:
    print("LangSmith 키 없음 — 트레이싱 비활성화")
```


```python
# OpenAI 연결 ping — 정상이면 짧은 응답 한 줄이 출력됨
from langchain_openai import ChatOpenAI

_ping_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_ping = _ping_llm.invoke("한국어로 'pong' 한 단어만 답해.")
print(f"OpenAI ping → {_ping.content!r}")
```

## 2. 매뉴얼 파일 로드

5개 매뉴얼: `alarm_code_guide.md`, `troubleshooting_guide.md`, `operation_policy.md`, `system_user_manual.md`, `faq.md`


```python
MANUAL_DIR = PROJECT_ROOT / "data" / "manuals"
MANUAL_FILES = [
    "alarm_code_guide.md",
    "troubleshooting_guide.md",
    "operation_policy.md",
    "system_user_manual.md",
    "faq.md",
]

raw_manuals = {}
for fname in MANUAL_FILES:
    path = MANUAL_DIR / fname
    text = path.read_text(encoding="utf-8")
    raw_manuals[fname] = text
    print(f"  [{fname}] {len(text):,} chars")
```

## 3. `section_id` 기준 chunk 생성 + metadata

매뉴얼 헤더 패턴:
- `## SECTION-ID | 제목` (sop / policy / system_manual / faq)
- `### SECTION-ID | 제목` (alarm_code_guide 의 개별 코드 anchor)

section_id 정규식: `[A-Z]+-[A-Z0-9-]+` (예: `SOP-TEMP-001`, `AC-TEMP-C-001`, `POL-SLA-001`, `FAQ-004`).

각 chunk metadata:
- `file_name` : 출처 매뉴얼
- `section_id` : anchor 식별자
- `title` : header 의 `|` 뒤 제목
- `citation` : LLM 응답에 그대로 인용 가능한 라벨 (`[SECTION-ID] 제목`)


```python
import re
from langchain_core.documents import Document

# 헤더: ## 또는 ### 으로 시작하고 SECTION-ID | TITLE 형태
HEADER_RE = re.compile(
    r"^(?P<hashes>#{2,3})\s+(?P<sid>[A-Z]+-[A-Z0-9-]+)\s*\|\s*(?P<title>.+?)\s*$",
    re.MULTILINE,
)


def split_by_section(file_name: str, text: str):
    """한 매뉴얼을 section_id 헤더 위치로 잘라 Document 리스트로 반환."""
    matches = list(HEADER_RE.finditer(text))
    if not matches:
        return []
    docs = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].rstrip()
        sid = m.group("sid")
        title = m.group("title").strip()
        # citation 라벨: 너무 길어지지 않도록 60자 내외 보장
        citation = f"[{sid}] {title}"
        if len(citation) > 60:
            citation = citation[:57] + "..."
        docs.append(
            Document(
                page_content=body,
                metadata={
                    "file_name": file_name,
                    "section_id": sid,
                    "title": title,
                    "citation": citation,
                },
            )
        )
    return docs


chunks = []
for fname, text in raw_manuals.items():
    chunks.extend(split_by_section(fname, text))

print(f"총 chunk 수: {len(chunks)}")
print()
print("파일별 chunk 분포:")
from collections import Counter
for fname, n in Counter(c.metadata["file_name"] for c in chunks).items():
    print(f"  {fname}: {n}")
print()
print("샘플 (첫 3개 chunk metadata + 본문 일부):")
for c in chunks[:3]:
    print(f"  · {c.metadata['citation']}  ({c.metadata['file_name']})")
    print(f"    body[:80] = {c.page_content[:80]!r}")
```

## 4. FAISS vectorstore

임베딩: `text-embedding-3-small` (1536 dim, 비용 효율적).


```python
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

embedding = OpenAIEmbeddings(model="text-embedding-3-small")
vectordb = FAISS.from_documents(chunks, embedding)
print(f"FAISS index 생성 완료 — 벡터 {vectordb.index.ntotal}개")
```

## 5. retriever + 빠른 sanity check


```python
retriever = vectordb.as_retriever(search_kwargs={"k": 4})

# Sanity: TEMP-H-001 의미 질의 → AC-TEMP-H-001 chunk가 top hit으로 와야 함
_test_q = "TEMP-H-001 알람의 의미와 임계치는?"
for i, d in enumerate(retriever.invoke(_test_q), 1):
    print(f"  [{i}] {d.metadata['citation']}  ({d.metadata['file_name']})")
```

## 6. `retrieve_manual_knowledge` tool

Agent 가 호출할 수 있는 검색 도구. 단순히 본문만 넘기면 LLM 이 인용을 빠뜨릴 수 있으므로, **각 chunk 머리에 citation 라벨을 부착**해 LLM 이 그대로 인용하도록 유도합니다.


```python
from langchain.tools import tool

@tool
def retrieve_manual_knowledge(query: str) -> str:
    """FDC-Monitoring 시스템의 사내 매뉴얼(알람 코드, SOP, 운영 정책, 시스템 사용법, FAQ)에서 정보를 검색합니다.

    다음 유형 질문에 사용하세요:
    - 알람 코드의 의미·임계치·원인 (예: TEMP-H-001, PRES-C-001)
    - SOP/조치 절차 (예: 챔버 과열, 진공 누설, EAP 통신 단절)
    - 운영 정책 (권한, SLA, escalation, 임계치 변경 절차)
    - 시스템 사용법 (Trend Chart, VOC 등록, 권한 신청)
    - FAQ 항목

    반환 형식: 각 검색 결과 앞에 `[SECTION-ID] 제목` 인용 라벨이 붙어 있습니다.
    답변 시 이 라벨을 그대로 인용하세요.
    """
    docs = vectordb.similarity_search(query, k=4)
    if not docs:
        return "관련 매뉴얼 항목을 찾지 못했습니다."
    blocks = []
    for d in docs:
        block = (
            f"### {d.metadata['citation']}\n"
            f"(출처: {d.metadata['file_name']})\n\n"
            f"{d.page_content}"
        )
        blocks.append(block)
    return "\n\n---\n\n".join(blocks)


# 도구 호출 미리보기
_preview = retrieve_manual_knowledge.invoke({"query": "GAS-W-001 가스 잔량 부족 처리"})
print(_preview[:600])
print("...")
```

## 7. Agent 생성

최소 구성: LLM + 단일 도구 (`retrieve_manual_knowledge`).

System prompt 핵심:
- 매뉴얼 검색이 필요한 질문은 반드시 도구를 호출하라
- 답변에는 `[SECTION-ID]` 라벨로 근거를 인용하라
- 매뉴얼에서 근거를 찾지 못하면 "근거를 찾을 수 없습니다" 라고 솔직히 말하라


```python
from langchain.agents import create_agent

agent_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

SYSTEM_PROMPT = (
    "너는 반도체 FDC-Monitoring 시스템의 VOC 응답 에이전트야.\n"
    "\n"
    "행동 원칙:\n"
    "1. 알람 코드·SOP·운영 정책·시스템 사용법·FAQ 관련 질문은 먼저 retrieve_manual_knowledge 도구로 매뉴얼을 검색해.\n"
    "2. 도구가 반환한 각 블록의 [SECTION-ID] 인용 라벨을 답변 본문에 그대로 인용해 (예: [TEMP-H-001 챔버 과열 High …] 형식).\n"
    "3. 매뉴얼 근거가 부족하면 추측하지 말고 '현재 지식베이스에서 근거를 찾을 수 없습니다.'라고 명확히 말해.\n"
    "4. 존재하지 않는 알람 코드·설비를 사용자가 언급하면 그 사실을 짚어주고, 정확한 ID를 재확인하도록 안내해.\n"
    "5. 답변은 한국어로, 핵심 → 절차 → 인용 순서로 간결하게."
)

agent = create_agent(
    model=agent_llm,
    tools=[retrieve_manual_knowledge],
    system_prompt=SYSTEM_PROMPT,
)
print("Agent 준비 완료")
```

## 8. VOC 테스트 (8건)

`data/voc/voc_samples.json` 의 핵심 VOC 중 난이도가 분산된 8건을 선정해 agent 에 던집니다.

| 선정 ID | 난이도 | 특징 |
|---|---|---|
| VOC-2026-0001 | easy | TEMP-H-001 의미 문의 |
| VOC-2026-0008 | easy | GAS-W-001 발생 처리 (FAQ 연계) |
| VOC-2026-0009 | medium | TEMP-H-001 조치 절차 |
| VOC-2026-0013 | medium | COMM-H-001 EAP 통신 단절 |
| VOC-2026-0017 | hard | 챔버 과열 증상 (코드 미명시) |
| VOC-2026-0019 | hard | Trend Chart 비어 있음 |
| VOC-2026-0023 | edge | RF tune cap fine-tuning (out-of-scope) |
| VOC-2026-0027 | trap | TEMP-Z-999 존재하지 않는 코드 |


```python
import json

VOC_PATH = PROJECT_ROOT / "data" / "voc" / "voc_samples.json"
all_vocs = json.loads(VOC_PATH.read_text(encoding="utf-8"))["vocs"]
voc_by_id = {v["voc_id"]: v for v in all_vocs}

TEST_IDS = [
    "VOC-2026-0001",  # easy
    "VOC-2026-0008",  # easy
    "VOC-2026-0009",  # medium
    "VOC-2026-0013",  # medium
    "VOC-2026-0017",  # hard
    "VOC-2026-0019",  # hard
    "VOC-2026-0023",  # edge — out-of-scope
    "VOC-2026-0027",  # trap — 존재하지 않는 코드
]

test_vocs = [voc_by_id[i] for i in TEST_IDS]
print(f"테스트 VOC {len(test_vocs)}건 선정")
for v in test_vocs:
    print(f"  · [{v['voc_id']}] ({v['difficulty']}) {v['title']}")
```


```python
def run_agent_on_voc(voc):
    """VOC 1건을 agent에 던지고, 도구 호출 흐름 + 최종 답변을 사람이 보기 좋게 출력."""
    print("=" * 80)
    print(f"[{voc['voc_id']}] difficulty={voc['difficulty']} | category={voc['category']}")
    print(f"  Q: {voc['content']}")
    print("-" * 80)

    result = agent.invoke({"messages": [("user", voc["content"])]})

    # 도구 호출 추적
    for msg in result["messages"]:
        msg_type = type(msg).__name__
        if msg_type == "AIMessage" and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                args = tc["args"]
                q = args.get("query", args) if isinstance(args, dict) else args
                print(f"  ▶ tool [{tc['name']}] query = {q!r}")
        elif msg_type == "ToolMessage":
            # 도구가 반환한 결과의 첫 줄(citation 라벨)만 미리 보여줌
            preview = msg.content.split("\n")[0][:90]
            print(f"    ↳ tool result head: {preview}")

    final = result["messages"][-1].content
    print("-" * 80)
    print("  [최종 답변]")
    for line in final.splitlines():
        print(f"  {line}")
    print("=" * 80)
    print()
    return result
```


```python
# 8건 순차 실행 — 첫 2건만 먼저 돌려보고 나머지는 별 셀에서 실행해도 됨
for v in test_vocs[:2]:
    run_agent_on_voc(v)
```


```python
for v in test_vocs[2:5]:  # medium 2 + hard 1
    run_agent_on_voc(v)
```


```python
for v in test_vocs[5:]:   # hard 1 + edge 1 + trap 1
    run_agent_on_voc(v)
```

## 9. MVP 점검 포인트

각 VOC 답변을 보고 직접 체크해 보세요.

| VOC | 기대 행동 |
|---|---|
| 0001 (easy) | `[AC-TEMP-H-001 …]` 인용 + 임계치(setpoint+20°C) 명시 |
| 0008 (easy) | `[FAQ-004 …]` 또는 `[AC-GAS-W-001 …]` 인용 |
| 0009 (medium) | `[SOP-TEMP-001 …]` 인용 + 단계별 절차 |
| 0013 (medium) | `[SOP-COMM-001 …]` 인용 + EAP 재시작 권한 언급 |
| 0017 (hard) | 코드 없이도 TEMP-H-001 / SOP-TEMP-001 후보 제시 |
| 0019 (hard) | `[FAQ-002 …]` 또는 `[SM-TRD-002 …]` 인용 |
| 0023 (edge) | "근거를 찾을 수 없음" + `POL-SCOPE-001` 인용 (out-of-scope) |
| 0027 (trap) | TEMP-Z-999 가 등록되지 않은 코드임을 명시, 재확인 요청 |

## 다음 단계 (별도 노트북/스크립트로 이어 갈 후보)

- `eval_groundtruth.json` 으로 자동 채점 (`gold_docs` recall, `gold_key_points` containment)
- BM25 + dense 하이브리드 검색
- LLM-as-Judge 기반 인용 정확성 검증
- 멀티턴 명확화 (multi-turn VOC 처리)
- src 모듈화 + Streamlit demo
