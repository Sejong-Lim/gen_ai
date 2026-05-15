# FDC-Monitoring AI System — VOC Response Agent

> 반도체/제조 현장의 설비 이상 감지 시스템(FDC) 기반 **VOC 응답 Agent** 구축을 위한 가짜 기업 데이터 생태계와 RAG·Agent 파이프라인.

이 저장소는 3일 데모를 위한 **Day 1 산출물(데이터 레이어)** 의 결과물입니다. Day 2(인덱싱·검색), Day 3(Agent·Guardrail·평가)은 후속으로 추가됩니다.

---

## 1. 프로젝트 개요

엔지니어가 등록한 VOC(알람 해석, 조치 방법, 권한 문의, 데이터 조회 오류 등)에 대해 내부 매뉴얼·운영 가이드·FAQ·SOP·과거 VOC 이력을 근거로 6-section 표준 응답을 자동 생성하는 RAG 기반 상담 자동화 Agent를 구축합니다.

**시스템 이름**: FDC-Monitoring AI System
**대상 사용자**: 설비/공정 엔지니어, 운영 담당자, 현장 대응 담당자

**답변 6-section 표준 포맷**:
1. 요약 답변 → 2. 근거 문서 → 3. 상세 설명 → 4. 권장 조치 → 5. 추가 확인 질문 → 6. 신뢰도 점수

근거 부족 시 "**현재 지식베이스에서 근거를 찾을 수 없습니다**"로 명시적 거절. 7-Layer Guardrail로 hallucination을 방지합니다.

---

## 2. 디렉토리 구조

```
Project/
├── data/
│   ├── _meta/
│   │   └── source_of_truth.yaml         # ★ 모든 ID/매핑의 단일 진실 공급원
│   ├── manuals/                         # 매뉴얼 5종 (anchor 부여)
│   │   ├── system_user_manual.md        # 10 sections (SM-*)
│   │   ├── alarm_code_guide.md          # 42 alarm codes (AC-*)
│   │   ├── troubleshooting_guide.md     # 19 SOPs (SOP-*)
│   │   ├── operation_policy.md          # 10 policies (POL-*)
│   │   └── faq.md                       # 10 FAQs (FAQ-*)
│   ├── db/                              # CSV 마스터·이력
│   │   ├── equipment_master.csv         # 30대 설비
│   │   ├── alarm_code_master.csv        # 42 알람코드
│   │   ├── user_master.csv              # 25 사용자
│   │   ├── alarm_history.csv            # 500건 발생 이력
│   │   └── voc_history.csv              # 150건 과거 VOC
│   ├── voc/
│   │   ├── voc_samples.json             # ★ 100건 VOC (핵심 30건 + 일반 70건)
│   │   └── voc_samples.csv
│   └── evaluation/
│       ├── test_questions.json          # 50 평가 문항
│       ├── eval_groundtruth.json        # gold labels
│       └── eval_edge_cases.json         # Edge/Trap/Multi-turn 18건
├── scripts/
│   ├── build_db.py                      # SOT → 5 CSV 파생
│   ├── build_voc.py                     # 핵심 30 + 양산 70 → JSON/CSV
│   ├── build_eval.py                    # 평가 데이터셋 3종 생성
│   └── validate_integrity.py            # ★ 무결성 검증 (CI용)
├── project_brief.txt.txt
└── README.md
```

---

## 3. 데이터 설계 핵심

### 3.1 명명 규칙 (machine-friendly)

| 자원 | 패턴 | 예시 |
|---|---|---|
| Equipment ID | `{공정}-{설비type}-{호기}` | `THIN-CVD-02`, `ETCH-DRY-03`, `IMP-HCI-01` |
| Alarm Code | `{Cat}-{Sev}-{Seq}` | `TEMP-H-001`, `PRES-C-001`, `RF-M-001` |
| SOP ID | `SOP-{Cat}-{###}` | `SOP-TEMP-001` |
| Section Anchor | `{prefix}-{id}` (헤더 첫 토큰) | `AC-TEMP-H-001`, `POL-PERM-002` |
| VOC ID | `VOC-2026-{####}` | `VOC-2026-0042` |
| Lot ID | `LOT-{YYYYMMDD}-{###}` | `LOT-20260512-017` |

매뉴얼 헤더는 `## {SECTION_ID} | {Title}` 형식 — 첫 토큰이 section_id 이므로 정규식 추출이 단순합니다.

### 3.2 Source of Truth (`data/_meta/source_of_truth.yaml`)

모든 ID·매핑이 **하나의 YAML**에서 시작합니다.
- 8 processes / 14 equipment types / 5 severities / 12 alarm categories
- **42 alarm codes** — 각 코드의 임계치·일반적 원인·적용 설비·관련 SOP 매핑
- **19 SOPs** — SOP↔alarm code 양방향 매핑
- 30 equipment / 25 users / 10 policies / 10 manual sections / 10 FAQ sections

매뉴얼·CSV·VOC·평가셋은 모두 이 파일에서 파생되며, `validate_integrity.py` 가 모든 cross-reference를 검증합니다.

### 3.3 의도된 KB 결함 (Hallucination 방지 테스트용)

- **Orphan codes** (7개): `TEMP-W-001`, `PRES-W-001`, `GAS-W-001`, `HV-W-001`, `DOSE-W-001`, `COMM-W-002`, `MECH-W-001` 은 알람 코드 마스터에는 존재하나 표준 SOP가 매핑되지 않음. Agent가 "SOP 없음"을 명확히 답해야 함.
- **Out-of-scope policy** (`POL-SCOPE-001`): 벤더 내부 파라미터·recipe 최적화·MES 사용법·인사·보안·물리적 정비 — 6개 영역을 명시적으로 KB 밖으로 선언. Edge VOC 평가에 직결.

---

## 4. VOC 100건 — 분포

### 4.1 핵심 30건 (`is_core=true`)

| Difficulty | 건수 | 평가 포인트 |
|---|---:|---|
| **Easy** | 8 | 알람코드 직매칭 — 단일 문서 (Recall@5) |
| **Medium** | 8 | 알람코드 + 설비 type + SOP 결합 (Citation precision) |
| **Hard** | 6 | 알람코드 없이 증상만 (의미 검색 성능) |
| **Edge** | 4 | 근거 부족 — "근거 없음" 응답 필수 (Refusal accuracy) |
| **Trap** | 2 | 존재하지 않는 코드/설비 (Entity validation) |
| **Multi-turn** | 2 | 정보 부족 → 명확화 질문 필요 |

핵심 30건은 다음 정보를 모두 포함합니다:
- `expected_key_points` — 정답 핵심 포인트 (LLM-judge 채점용)
- `expected_answer` — 6-section 표준 응답 예시
- `source_document_hint` — gold citation (매뉴얼 파일#anchor)
- `expected_refusal` — Refusal accuracy 채점용
- `expected_clarification` — Multi-turn 명확화 평가용

### 4.2 일반 70건 (`is_core=false`, 카테고리 분포 채움)

10개 카테고리에 걸쳐 분포되며 (예: 알람 코드 의미 문의 11, VOC 처리 상태 문의 10, …) 템플릿 기반 양산.

---

## 5. 무결성 검증 결과

```
======================================================================
FDC-Monitoring AI System — 데이터 레이어 무결성 검증
======================================================================

[A] Source-of-truth 내부 무결성
[B] 매뉴얼 anchor 추출 및 SOT 일치
[C] DB CSV ↔ SOT 일치
[D] VOC ↔ 매뉴얼 citation 무결성
[E] 평가셋 ↔ 매뉴얼 citation 무결성
[F] 분포 검증
    카테고리 분포:
      조치 방법 문의: 23
      알람 코드 의미 문의: 20
      VOC 처리 상태 문의: 12
      알람 원인 문의: 11
      Trend Chart 조회 오류: 8
      권한 문제: 6
      데이터 누락 문의: 5
      임계치 설정 문의: 5
      설비 상태 불일치: 5
      시스템 접속 오류: 5
    핵심 30건 difficulty 분포: easy=8, edge=4, hard=6, medium=8, multi_turn=2, trap=2

======================================================================
검사 통과: 23
경고:       0
오류:       0
======================================================================

[OK] 모든 무결성 검증 통과.
```

검사 그룹별 항목 (요약):
- **A. SOT 내부**: 알람→SOP / section_id 패턴 / 적용 설비 / SOP↔코드 양방향 / 설비 type 일관성 / severity·category 일관성
- **B. 매뉴얼 anchor**: 정의↔실재 양방향, 본문 내부 cross-reference 무결성
- **C. DB CSV**: 마스터↔SOT 완전 일치, 알람 발생 이력의 설비-알람 적용성 검증 (500건)
- **D. VOC**: `source_document_hint`의 매뉴얼 anchor 실재, trap 제외 entity 실재성, 핵심 30건 difficulty 라벨
- **E. 평가셋**: gold_docs anchor 실재, refusal과 difficulty 일관성
- **F. 분포**: 핵심 30건의 6개 difficulty 모두 포함, 카테고리 다양성

---

## 6. 실행 방법

### 6.1 환경
- Python 3.7+
- `pip install pyyaml`

### 6.2 데이터 (재)생성 — 순서대로

```bash
# 1) DB CSV 5종 — SOT 에서 파생, 시드 고정
python scripts/build_db.py

# 2) VOC 100건 — 핵심 30 손정의 + 양산 70
python scripts/build_voc.py

# 3) 평가셋 3종 — 핵심 30 + 추가 20
python scripts/build_eval.py

# 4) 무결성 검증 — 23개 검사 모두 통과해야 함
python scripts/validate_integrity.py
```

CI 또는 PR 검증 시 4번만 실행하면 됩니다 (다른 산출물에 의존).

### 6.3 데이터 수정 시 작업 흐름

1. `data/_meta/source_of_truth.yaml` 수정 (예: 새 알람코드 추가, SOP 신설)
2. `data/manuals/*.md` 에 해당 section 추가 (`## {SECTION_ID} | {Title}` 헤더)
3. 위 4단계 스크립트 재실행
4. validate가 통과하지 않으면 수정 반복

---

## 7. 후속 작업 (Day 2~3)

### Day 2 — 인덱싱·검색
- Markdown-aware chunking + metadata 부착
- BM25 + OpenAI `text-embedding-3-large` 하이브리드 검색
- `bge-reranker-v2-m3` 로 top-20 → top-5 재정렬

### Day 3 — Agent + Guardrail + 평가
- Intent/Entity 추출 (GPT-4o JSON-mode)
- 6-section Response Generator
- 7-Layer Guardrail (citation·entity·groundedness·threshold·confidence·OOS 매칭)
- Jupyter Notebook 데모 (04_agent_demo.ipynb) + Ablation 비교 (05_guardrail_ablation.ipynb)

---

## 8. 핵심 설계 결정 요약

| 결정 | 선택 | 이유 |
|---|---|---|
| LLM/임베딩 | OpenAI (GPT-4o, text-embedding-3-large) | 구현 속도·한국어 품질 |
| Reranker | bge-reranker-v2-m3 (예외 import) | OpenAI 미제공, 비용·속도 우위 |
| 데모 UI | Jupyter Notebook 전용 | 발표 시 코드 가시성 + UI 작업 시간 절감 |
| VOC 생성 | 핵심 30 손정의 + 양산 70 | 시연 신뢰도와 평가 다양성 동시 확보 |
| Citation 표기 | 내부 기계식 / 사용자 노출 사람식 (단일 메타데이터에서 변환) | 양쪽 장점 + 매핑 테이블 제거 |
| 명명 일관성 | section_id를 매뉴얼 헤더 첫 토큰으로 | 정규식 추출 단순, 디버깅 용이 |

---

## 9. 라이선스

본 저장소는 학습·시연용 가짜 데이터를 포함합니다. 모든 사번·이메일·VOC 내용은 가상이며 실제 인물·기업과 무관합니다.
