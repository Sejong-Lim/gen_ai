#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_eval.py — 평가 데이터셋 3종 생성.

산출물:
  data/evaluation/test_questions.json   (50 문항)
  data/evaluation/eval_groundtruth.json (gold labels)
  data/evaluation/eval_edge_cases.json  (edge/trap/multi-turn subset)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOC_PATH = ROOT / "data" / "voc" / "voc_samples.json"
EVAL_DIR = ROOT / "data" / "evaluation"


# =============================================================================
# 추가 평가 문항 (핵심 30 + 추가 20 = 50)
# - 핵심 VOC와 별도로, 다양한 표현·다중 문서·trap variant를 포함
# =============================================================================
ADDITIONAL_TESTS = [
    # ---- Hard paraphrase (5) ----
    {
        "qid": "Q-031",
        "question": "CVD 챔버 진공이 안 잡혀요. base pressure가 1e-5 Torr 근처에서 더 안 내려갑니다.",
        "category": "조치 방법 문의",
        "difficulty": "hard",
        "expected_intent": "action_howto",
        "expected_entities": {"alarm_code": "VAC-H-001", "equipment_type": "CVD"},
        "gold_docs": [
            "alarm_code_guide.md#sec-AC-VAC-H-001",
            "troubleshooting_guide.md#sec-SOP-VAC-001",
        ],
        "gold_key_points": [
            "VAC-H-001 진공도 미달 가능성 (base pressure > 5e-6 Torr)",
            "SOP-VAC-001 단계별 점검",
            "viewport → O-ring → feedthrough 순서",
        ],
        "expected_refusal": False,
        "min_citations": 2,
    },
    {
        "qid": "Q-032",
        "question": "RF가 자꾸 reflected가 높게 잡힙니다. 반사파가 forward의 8% 정도 나옵니다.",
        "category": "조치 방법 문의",
        "difficulty": "hard",
        "expected_intent": "action_howto",
        "expected_entities": {"alarm_code": "RF-M-001"},
        "gold_docs": [
            "alarm_code_guide.md#sec-AC-RF-M-001",
            "troubleshooting_guide.md#sec-SOP-RF-002",
        ],
        "gold_key_points": [
            "RF-M-001 Matching 불량 (reflected > 5%)",
            "Auto-tune 재실행",
            "Tune cap 끝단 도달 확인",
        ],
        "expected_refusal": False,
        "min_citations": 2,
    },
    {
        "qid": "Q-033",
        "question": "EAP 통신이 1분 이상 끊겼다 붙었다 합니다. 어떻게 대응하나요?",
        "category": "조치 방법 문의",
        "difficulty": "hard",
        "expected_intent": "action_howto",
        "expected_entities": {"alarm_code": "COMM-H-001"},
        "gold_docs": [
            "alarm_code_guide.md#sec-AC-COMM-H-001",
            "troubleshooting_guide.md#sec-SOP-COMM-001",
        ],
        "gold_key_points": [
            "COMM-H-001 EAP 단절 (60초 이상)",
            "EAP 프로세스 재시작 (EQ_ENG 권한)",
            "수동 운영 모드는 PROC_ENG 권한, 최대 4시간",
        ],
        "expected_refusal": False,
        "min_citations": 2,
    },
    {
        "qid": "Q-034",
        "question": "공정 가스가 라인에서 새는 것 같아 보입니다. 의심되는 게 뭐고 뭐부터 해야 하나요?",
        "category": "조치 방법 문의",
        "difficulty": "hard",
        "expected_intent": "action_howto",
        "expected_entities": {"alarm_code": "GAS-H-001"},
        "gold_docs": [
            "alarm_code_guide.md#sec-AC-GAS-H-001",
            "troubleshooting_guide.md#sec-SOP-GAS-002",
            "troubleshooting_guide.md#sec-SOP-GAS-001",
        ],
        "gold_key_points": [
            "Toxic Gas 동시 검출 우선 확인 → SOP-GAS-001",
            "GAS-H-001 일반 절차",
            "해당 가스 isolation 후 He leak test",
        ],
        "expected_refusal": False,
        "min_citations": 2,
    },
    {
        "qid": "Q-035",
        "question": "Implanter에서 dose 값이 wafer 가운데와 가장자리가 차이 나요. 1% 정도입니다.",
        "category": "조치 방법 문의",
        "difficulty": "hard",
        "expected_intent": "action_howto",
        "expected_entities": {"alarm_code": "DOSE-H-001"},
        "gold_docs": [
            "alarm_code_guide.md#sec-AC-DOSE-H-001",
            "troubleshooting_guide.md#sec-SOP-DOSE-001",
        ],
        "gold_key_points": [
            "DOSE-H-001 균일도 임계치 1.5% (1σ)",
            "1%면 임계치 이내",
            "추이 모니터링 권장",
        ],
        "expected_refusal": False,
        "min_citations": 1,
    },

    # ---- Cross-doc combination (5) ----
    {
        "qid": "Q-036",
        "question": "임계치를 바꾸려면 권한이 어떻게 되고 신청서는 어디서 작성하나요?",
        "category": "임계치 설정 문의",
        "difficulty": "medium",
        "expected_intent": "permission_policy",
        "expected_entities": {},
        "gold_docs": [
            "operation_policy.md#sec-POL-PERM-002",
            "operation_policy.md#sec-POL-CHG-001",
            "system_user_manual.md#sec-SM-ALM-002",
        ],
        "gold_key_points": [
            "신청 EQ_ENG / 승인 PROC_ENG",
            "Critical은 공정 PM 추가 승인",
            "알람 상세 화면 [임계치 변경 신청] 버튼",
            "정량적 근거 필수",
        ],
        "expected_refusal": False,
        "min_citations": 2,
    },
    {
        "qid": "Q-037",
        "question": "Trend Chart에서 CSV 다운로드 버튼이 회색입니다. 누구한테 권한이 있나요?",
        "category": "권한 문제",
        "difficulty": "medium",
        "expected_intent": "permission_policy",
        "expected_entities": {},
        "gold_docs": [
            "operation_policy.md#sec-POL-PERM-001",
            "system_user_manual.md#sec-SM-TRD-001",
        ],
        "gold_key_points": [
            "EQ_ENG 이상만 다운로드 가능",
            "회당 1GB / 일일 10GB 제한",
        ],
        "expected_refusal": False,
        "min_citations": 1,
    },
    {
        "qid": "Q-038",
        "question": "알람 이력을 6개월 전까지 거슬러 보고 싶은데 가능한가요?",
        "category": "데이터 누락 문의",
        "difficulty": "medium",
        "expected_intent": "data_lookup",
        "expected_entities": {},
        "gold_docs": [
            "operation_policy.md#sec-POL-DATA-001",
            "faq.md#sec-FAQ-009",
        ],
        "gold_key_points": [
            "알람 이력 메타데이터 2년 보존",
            "Trend 원본 90일 (이후 1분 평균 다운샘플)",
        ],
        "expected_refusal": False,
        "min_citations": 1,
    },
    {
        "qid": "Q-039",
        "question": "신규 사용자 등록은 어떻게 하나요? 본인이 신청 가능한가요?",
        "category": "권한 문제",
        "difficulty": "medium",
        "expected_intent": "permission_policy",
        "expected_entities": {},
        "gold_docs": [
            "operation_policy.md#sec-POL-ACC-001",
        ],
        "gold_key_points": [
            "사내 IT 포털에서 신청",
            "부서장 승인 필요",
            "관리자 처리 영업일 1일 이내",
        ],
        "expected_refusal": False,
        "min_citations": 1,
    },
    {
        "qid": "Q-040",
        "question": "Critical 알람의 임계치 변경은 누가 승인하나요?",
        "category": "임계치 설정 문의",
        "difficulty": "medium",
        "expected_intent": "permission_policy",
        "expected_entities": {"severity": "C"},
        "gold_docs": [
            "operation_policy.md#sec-POL-PERM-002",
        ],
        "gold_key_points": [
            "PROC_ENG 1차 승인",
            "공정 PM 추가 승인 필요",
            "EHS 연계 시 EHS 부서 추가 승인",
        ],
        "expected_refusal": False,
        "min_citations": 1,
    },

    # ---- Out-of-scope variants (4) ----
    {
        "qid": "Q-041",
        "question": "MES 시스템에서 lot tracking은 어떻게 봅니까?",
        "category": "조치 방법 문의",
        "difficulty": "edge",
        "expected_intent": "out_of_scope",
        "expected_entities": {},
        "gold_docs": ["operation_policy.md#sec-POL-SCOPE-001"],
        "gold_key_points": [
            "MES 사용법은 Out-of-Scope",
            "MES 매뉴얼 별도 참조",
        ],
        "expected_refusal": True,
        "min_citations": 1,
    },
    {
        "qid": "Q-042",
        "question": "사번 U0001 사용자의 휴가 일정을 확인하고 싶습니다.",
        "category": "권한 문제",
        "difficulty": "edge",
        "expected_intent": "out_of_scope",
        "expected_entities": {"user_id": "U0001"},
        "gold_docs": ["operation_policy.md#sec-POL-SCOPE-001"],
        "gold_key_points": [
            "인사 정보는 Out-of-Scope",
            "HR 시스템 참조",
        ],
        "expected_refusal": True,
        "min_citations": 1,
    },
    {
        "qid": "Q-043",
        "question": "사내 네트워크 방화벽 룰을 변경하려면 어떻게 하나요?",
        "category": "시스템 접속 오류",
        "difficulty": "edge",
        "expected_intent": "out_of_scope",
        "expected_entities": {},
        "gold_docs": ["operation_policy.md#sec-POL-SCOPE-001"],
        "gold_key_points": [
            "보안 운영은 Out-of-Scope",
            "사내 IT 보안 부서 영역",
        ],
        "expected_refusal": True,
        "min_citations": 1,
    },
    {
        "qid": "Q-044",
        "question": "CVD chamber의 일반적 dry-clean recipe 추천 시간을 알려주세요.",
        "category": "조치 방법 문의",
        "difficulty": "edge",
        "expected_intent": "out_of_scope",
        "expected_entities": {"equipment_type": "CVD"},
        "gold_docs": ["operation_policy.md#sec-POL-SCOPE-001"],
        "gold_key_points": [
            "Recipe 내용·최적화는 Out-of-Scope",
            "공정팀/벤더 영역",
        ],
        "expected_refusal": True,
        "min_citations": 1,
    },

    # ---- Trap variants (3) ----
    {
        "qid": "Q-045",
        "question": "FLOW-C-001 Critical 알람이 떴습니다. 어떻게 처리하나요?",
        "category": "조치 방법 문의",
        "difficulty": "trap",
        "expected_intent": "alarm_meaning",
        "expected_entities": {"alarm_code": "FLOW-C-001"},
        "gold_docs": ["operation_policy.md#sec-POL-SCOPE-001"],
        "gold_key_points": [
            "FLOW-C-001은 등록되지 않은 코드 (FLOW 카테고리에는 Critical 없음)",
            "FLOW의 유효 코드는 H/M/W만 존재",
            "사용자 재확인 요청",
        ],
        "expected_refusal": True,
        "min_citations": 0,
    },
    {
        "qid": "Q-046",
        "question": "PHOTO-EUV-01 설비의 알람 이력을 보여주세요.",
        "category": "데이터 누락 문의",
        "difficulty": "trap",
        "expected_intent": "data_lookup",
        "expected_entities": {"equipment_id": "PHOTO-EUV-01"},
        "gold_docs": ["operation_policy.md#sec-POL-SCOPE-001"],
        "gold_key_points": [
            "PHOTO-EUV-01은 등록되지 않은 설비 ID",
            "PHOTO 등록 설비는 SCN-01/02/03, CTR-01/02",
            "재확인 요청",
        ],
        "expected_refusal": True,
        "min_citations": 0,
    },
    {
        "qid": "Q-047",
        "question": "VOC-2025-9999 처리 상태를 확인해 주세요.",
        "category": "VOC 처리 상태 문의",
        "difficulty": "trap",
        "expected_intent": "voc_status",
        "expected_entities": {"voc_id": "VOC-2025-9999"},
        "gold_docs": ["operation_policy.md#sec-POL-SCOPE-001"],
        "gold_key_points": [
            "VOC ID format 다르거나 미존재",
            "본 시스템 VOC ID 형식: VOC-2026-XXXX",
            "재확인 요청",
        ],
        "expected_refusal": True,
        "min_citations": 0,
    },

    # ---- Multi-turn / clarification (3) ----
    {
        "qid": "Q-048",
        "question": "설비가 이상해요",
        "category": "알람 원인 문의",
        "difficulty": "multi_turn",
        "expected_intent": "clarification_needed",
        "expected_entities": {},
        "gold_docs": ["system_user_manual.md#sec-SM-VOC-001"],
        "gold_key_points": [
            "정보 부족 — 명확화 질문 우선",
            "필요 정보: 설비 ID, 어떤 증상, 시점",
        ],
        "expected_refusal": False,
        "expected_clarification": True,
        "min_citations": 0,
    },
    {
        "qid": "Q-049",
        "question": "왜 처리가 안 되는 거죠?",
        "category": "VOC 처리 상태 문의",
        "difficulty": "multi_turn",
        "expected_intent": "clarification_needed",
        "expected_entities": {},
        "gold_docs": ["system_user_manual.md#sec-SM-VOC-002"],
        "gold_key_points": [
            "어떤 VOC ID인지 확인 필요",
            "현재 표시되는 상태는?",
        ],
        "expected_refusal": False,
        "expected_clarification": True,
        "min_citations": 0,
    },
    {
        "qid": "Q-050",
        "question": "TEMP 알람이 뜬 것 같아요",
        "category": "알람 원인 문의",
        "difficulty": "multi_turn",
        "expected_intent": "clarification_needed",
        "expected_entities": {"category": "TEMP"},
        "gold_docs": ["alarm_code_guide.md#sec-AC-TEMP-H-001"],
        "gold_key_points": [
            "TEMP 카테고리 5개 코드 안내 가능",
            "어떤 severity인지 확인 필요",
            "설비 ID 확인 필요",
        ],
        "expected_refusal": False,
        "expected_clarification": True,
        "min_citations": 0,
    },
]


def derive_from_core_vocs():
    """핵심 VOC 30건을 평가 항목 포맷으로 변환."""
    with open(VOC_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    core_vocs = [v for v in data["vocs"] if v.get("is_core")]
    tests = []
    for i, v in enumerate(core_vocs, start=1):
        tests.append({
            "qid": f"Q-{i:03d}",
            "question": v["content"],
            "title": v["title"],
            "category": v["category"],
            "difficulty": v["difficulty"],
            "expected_intent": _infer_intent(v),
            "expected_entities": _extract_entities(v),
            "gold_docs": v.get("source_document_hint", []),
            "gold_key_points": v.get("expected_key_points", []),
            "expected_refusal": v.get("expected_refusal", False),
            "expected_clarification": v["difficulty"] == "multi_turn",
            "min_citations": _min_citations(v),
            "source_voc_id": v["voc_id"],
        })
    return tests


def _infer_intent(v):
    cat = v["category"]
    if cat in ("알람 코드 의미 문의",):
        return "alarm_meaning"
    if cat in ("조치 방법 문의", "알람 원인 문의"):
        if v.get("expected_refusal"):
            return "out_of_scope"
        return "action_howto"
    if cat in ("권한 문제", "임계치 설정 문의"):
        return "permission_policy"
    if cat in ("Trend Chart 조회 오류", "데이터 누락 문의"):
        return "ui_lookup"
    if cat in ("VOC 처리 상태 문의",):
        return "voc_status"
    if cat in ("시스템 접속 오류",):
        return "access_issue"
    if cat in ("설비 상태 불일치",):
        return "status_lookup"
    return "general"


def _extract_entities(v):
    ent = {}
    if v.get("equipment_id"):
        ent["equipment_id"] = v["equipment_id"]
    if v.get("alarm_code"):
        ent["alarm_code"] = v["alarm_code"]
    return ent


def _min_citations(v):
    if v.get("expected_refusal"):
        return 1  # at least cite POL-SCOPE-001 or refusal source
    if v["difficulty"] == "multi_turn":
        return 0
    if v["difficulty"] in ("easy",):
        return 1
    return 2


def main():
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    derived = derive_from_core_vocs()
    tests = derived + ADDITIONAL_TESTS
    assert len(tests) == 50, f"expected 50, got {len(tests)}"

    # test_questions.json
    with open(EVAL_DIR / "test_questions.json", "w", encoding="utf-8") as f:
        json.dump({
            "meta": {
                "total": len(tests),
                "from_core_vocs": len(derived),
                "additional": len(ADDITIONAL_TESTS),
                "difficulty_dist": _count_by(tests, "difficulty"),
                "category_dist": _count_by(tests, "category"),
            },
            "tests": tests,
        }, f, ensure_ascii=False, indent=2)
    print(f"  [OK] test_questions.json  ({len(tests)} items)")

    # eval_groundtruth.json (gold-only view, 채점 스크립트가 빠르게 로드)
    gt = []
    for t in tests:
        gt.append({
            "qid": t["qid"],
            "gold_docs": t["gold_docs"],
            "gold_key_points": t["gold_key_points"],
            "expected_refusal": t["expected_refusal"],
            "expected_clarification": t.get("expected_clarification", False),
            "min_citations": t["min_citations"],
        })
    with open(EVAL_DIR / "eval_groundtruth.json", "w", encoding="utf-8") as f:
        json.dump({"groundtruth": gt}, f, ensure_ascii=False, indent=2)
    print(f"  [OK] eval_groundtruth.json  ({len(gt)} items)")

    # eval_edge_cases.json — Edge/Trap/Multi-turn 모음
    edge_items = [t for t in tests
                  if t["difficulty"] in ("edge", "trap", "multi_turn")]
    with open(EVAL_DIR / "eval_edge_cases.json", "w", encoding="utf-8") as f:
        json.dump({
            "meta": {
                "total": len(edge_items),
                "by_difficulty": _count_by(edge_items, "difficulty"),
            },
            "items": edge_items,
        }, f, ensure_ascii=False, indent=2)
    print(f"  [OK] eval_edge_cases.json  ({len(edge_items)} items)")


def _count_by(items, key):
    counts = {}
    for it in items:
        v = it.get(key, "unknown")
        counts[v] = counts.get(v, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    main()
