#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_voc.py — VOC 100건 생성.

- 핵심 30건(is_core=True): Easy/Medium/Hard/Edge/Trap/Multi-turn 라벨 포함 손으로 정의.
- 일반 70건(is_core=False): 템플릿 기반 양산 (시드 고정).

산출물:
  data/voc/voc_samples.json
  data/voc/voc_samples.csv
"""

import csv
import json
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml이 필요합니다.")

ROOT = Path(__file__).resolve().parent.parent
SOT_PATH = ROOT / "data" / "_meta" / "source_of_truth.yaml"
VOC_DIR = ROOT / "data" / "voc"
DB_DIR = ROOT / "data" / "db"


def load_sot():
    with open(SOT_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# =============================================================================
# 핵심 30건 — 손으로 정의
#   필드: voc_id, title, content, user_role, user_id, equipment_id, alarm_code,
#         category, priority, created_at, is_core, difficulty,
#         expected_refusal, source_document_hint, expected_key_points,
#         expected_answer
# =============================================================================
CORE_VOCS = [
    # ---------- Easy 8건 (알람 코드 의미 직접 문의) ----------
    {
        "voc_id": "VOC-2026-0001",
        "title": "TEMP-H-001 알람 의미가 궁금합니다",
        "content": "ETCH-DRY-01 CH-A에서 오늘 오후 TEMP-H-001 알람이 떴습니다. 이 알람 코드가 정확히 무엇을 의미하나요?",
        "user_role": "EQ_ENG", "user_id": "U0002",
        "equipment_id": "ETCH-DRY-01", "alarm_code": "TEMP-H-001",
        "category": "알람 코드 의미 문의", "priority": "NORMAL",
        "created_at": "2026-05-13 14:22:00",
        "is_core": True, "difficulty": "easy", "expected_refusal": False,
        "source_document_hint": ["alarm_code_guide.md#sec-AC-TEMP-H-001"],
        "expected_key_points": [
            "챔버 과열 High 알람", "임계치: setpoint + 20°C 초과",
            "자동 hold", "관련 SOP: SOP-TEMP-001"
        ],
        "expected_answer": "TEMP-H-001은 챔버 과열 High 알람으로, 챔버 온도가 recipe setpoint 대비 +20°C(예: setpoint 300°C 기준 320°C)를 초과했음을 의미합니다. Severity는 High이며 발생 시 자동으로 챔버 hold 됩니다. 단계별 조치는 SOP-TEMP-001을 따라 가스 공급 → 냉각수 → 히터 출력 → TC 응답 순으로 점검합니다. [알람코드설명서 §AC-TEMP-H-001]",
    },
    {
        "voc_id": "VOC-2026-0002",
        "title": "PRES-C-001 의미 문의",
        "content": "THIN-CVD-02에서 PRES-C-001 알람이 발생했습니다. Critical로 표시되는데 정확한 의미와 발생 조건이 궁금합니다.",
        "user_role": "OP", "user_id": "U0013",
        "equipment_id": "THIN-CVD-02", "alarm_code": "PRES-C-001",
        "category": "알람 코드 의미 문의", "priority": "HIGH",
        "created_at": "2026-05-14 03:15:00",
        "is_core": True, "difficulty": "easy", "expected_refusal": False,
        "source_document_hint": ["alarm_code_guide.md#sec-AC-PRES-C-001"],
        "expected_key_points": [
            "챔버 압력 Critical", "setpoint 대비 ±30% 초과",
            "즉시 hold", "관련 SOP: SOP-PRES-001"
        ],
        "expected_answer": "PRES-C-001은 챔버 압력 Critical 알람이며, process pressure가 setpoint 대비 ±30%를 초과한 경우 발생합니다. Critical severity로 즉시 챔버 hold가 적용되며, 일반적 원인은 TM 밸브 고착·펌프 정지·MFC 폭주입니다. 조치는 SOP-PRES-001을 참조하세요. [알람코드설명서 §AC-PRES-C-001]",
    },
    {
        "voc_id": "VOC-2026-0003",
        "title": "RF-C-001 알람 의미",
        "content": "ETCH-DRY-03 CH-B에서 RF-C-001 Critical이 떴습니다. 의미를 알려주세요.",
        "user_role": "EQ_ENG", "user_id": "U0002",
        "equipment_id": "ETCH-DRY-03", "alarm_code": "RF-C-001",
        "category": "알람 코드 의미 문의", "priority": "URGENT",
        "created_at": "2026-05-12 09:45:00",
        "is_core": True, "difficulty": "easy", "expected_refusal": False,
        "source_document_hint": ["alarm_code_guide.md#sec-AC-RF-C-001"],
        "expected_key_points": [
            "RF Reflected Power Critical", "Reflected/Forward > 30%",
            "즉시 RF off", "관련 SOP: SOP-RF-001"
        ],
        "expected_answer": "RF-C-001은 RF Reflected Power Critical 알람으로, 반사파(Reflected)와 진행파(Forward) 비율이 30%를 초과한 상태입니다. Critical이라 자동으로 RF가 off 되며, Matcher 단락이나 전극 contamination이 원인일 가능성이 높습니다. 조치는 SOP-RF-001을 참조하세요. [알람코드설명서 §AC-RF-C-001]",
    },
    {
        "voc_id": "VOC-2026-0004",
        "title": "VAC-H-001 알람 의미",
        "content": "THIN-PVD-01에서 VAC-H-001 High 알람. 진공도 미달이라고 하는데 어느 정도 미달인 건가요?",
        "user_role": "EQ_ENG", "user_id": "U0001",
        "equipment_id": "THIN-PVD-01", "alarm_code": "VAC-H-001",
        "category": "알람 코드 의미 문의", "priority": "NORMAL",
        "created_at": "2026-05-11 11:30:00",
        "is_core": True, "difficulty": "easy", "expected_refusal": False,
        "source_document_hint": ["alarm_code_guide.md#sec-AC-VAC-H-001"],
        "expected_key_points": [
            "진공도 미달 High", "base pressure > 5e-6 Torr",
            "목표 1e-6 Torr", "관련 SOP: SOP-VAC-001"
        ],
        "expected_answer": "VAC-H-001은 진공도 미달 High 알람으로, base pressure가 5e-6 Torr를 초과한 상태입니다. 정상 목표값은 1e-6 Torr 입니다. 펌프 성능 저하나 챔버 outgassing이 일반적 원인이며, 조치는 SOP-VAC-001을 따릅니다. [알람코드설명서 §AC-VAC-H-001]",
    },
    {
        "voc_id": "VOC-2026-0005",
        "title": "COMM-M-001 알람 의미",
        "content": "여러 설비에서 COMM-M-001 알람이 산발적으로 발생하고 있습니다. SECS/GEM 관련이라고 하는데 정확히 무엇인가요?",
        "user_role": "EQ_ENG", "user_id": "U0023",
        "equipment_id": "", "alarm_code": "COMM-M-001",
        "category": "알람 코드 의미 문의", "priority": "NORMAL",
        "created_at": "2026-05-13 10:05:00",
        "is_core": True, "difficulty": "easy", "expected_refusal": False,
        "source_document_hint": ["alarm_code_guide.md#sec-AC-COMM-M-001"],
        "expected_key_points": [
            "SECS/GEM 응답 지연", "S6F11 응답 시간 > 5초",
            "host load 증가 또는 buffer overflow", "관련 SOP: SOP-COMM-001"
        ],
        "expected_answer": "COMM-M-001은 SECS/GEM 응답 지연 알람으로, S6F11 메시지 응답 시간이 5초를 초과한 경우 발생합니다. Medium severity이며 진행은 계속되지만 host load 증가나 buffer overflow를 의심해야 합니다. 조치는 SOP-COMM-001을 참조하세요. [알람코드설명서 §AC-COMM-M-001]",
    },
    {
        "voc_id": "VOC-2026-0006",
        "title": "REC-W-001 의미",
        "content": "REC-W-001 Recipe 버전 불일치 경고가 떴습니다. 실제로 잘못된 recipe로 가동되고 있는 건가요?",
        "user_role": "PROC_ENG", "user_id": "U0008",
        "equipment_id": "ETCH-DRY-02", "alarm_code": "REC-W-001",
        "category": "알람 코드 의미 문의", "priority": "NORMAL",
        "created_at": "2026-05-14 16:20:00",
        "is_core": True, "difficulty": "easy", "expected_refusal": False,
        "source_document_hint": [
            "alarm_code_guide.md#sec-AC-REC-W-001",
            "faq.md#sec-FAQ-008"
        ],
        "expected_key_points": [
            "Recipe 버전 불일치 Warning", "설비 실행 버전 ≠ MES 최신",
            "대부분 단순 동기화 지연", "잘못된 recipe로 가동 아님"
        ],
        "expected_answer": "REC-W-001은 설비 실행 중 recipe 버전이 MES 등록 최신 버전과 다를 때 발생하는 Warning 알람입니다. 대부분 단순한 동기화 지연이며 잘못된 recipe로 가동되는 것은 아닙니다. 버전 차이가 1 버전 이내면 자동 동기화를 기다리고, 2 버전 이상이면 SOP-REC-001 5단계의 수동 동기화를 시도하세요. [FAQ §FAQ-008] [알람코드설명서 §AC-REC-W-001]",
    },
    {
        "voc_id": "VOC-2026-0007",
        "title": "DOSE-H-001 의미",
        "content": "IMP-HCI-01에서 DOSE-H-001 High 알람이 떴습니다. dose 균일도 관련이라는데 임계치가 어떻게 되나요?",
        "user_role": "PROC_ENG", "user_id": "U0011",
        "equipment_id": "IMP-HCI-01", "alarm_code": "DOSE-H-001",
        "category": "알람 코드 의미 문의", "priority": "HIGH",
        "created_at": "2026-05-12 13:10:00",
        "is_core": True, "difficulty": "easy", "expected_refusal": False,
        "source_document_hint": ["alarm_code_guide.md#sec-AC-DOSE-H-001"],
        "expected_key_points": [
            "Dose 균일도 High", "wafer 내 dose 균일도 (1σ) > 1.5%",
            "관련 SOP: SOP-DOSE-001"
        ],
        "expected_answer": "DOSE-H-001은 Dose 균일도 High 알람으로, wafer 내 dose 균일도(1σ)가 1.5%를 초과한 경우 발생합니다. beam scan profile drift나 Faraday 측정 오차가 일반적 원인이며, 조치는 SOP-DOSE-001을 따라 contamination 확인 → beam profile 측정 → calibration 순으로 진행합니다. [알람코드설명서 §AC-DOSE-H-001]",
    },
    {
        "voc_id": "VOC-2026-0008",
        "title": "GAS-W-001 발생",
        "content": "THIN-CVD-01에서 GAS-W-001 가스 잔량 부족 Warning이 떴습니다. 어떻게 처리하면 되나요?",
        "user_role": "OP", "user_id": "U0014",
        "equipment_id": "THIN-CVD-01", "alarm_code": "GAS-W-001",
        "category": "알람 코드 의미 문의", "priority": "NORMAL",
        "created_at": "2026-05-13 22:40:00",
        "is_core": True, "difficulty": "easy", "expected_refusal": False,
        "source_document_hint": [
            "alarm_code_guide.md#sec-AC-GAS-W-001",
            "faq.md#sec-FAQ-004"
        ],
        "expected_key_points": [
            "실린더 잔량 < 15%", "SOP 없음 — FAQ-004 참조",
            "가스 공급팀(내선 3000)에 교체 요청",
            "잔량 10% 이하에서 추가 알람 없음 — 운영 관리 필요"
        ],
        "expected_answer": "GAS-W-001은 실린더 잔량이 15% 이하일 때 발생하는 경고성 알람으로, 별도 SOP는 없습니다. 처리 절차는 사내 가스 공급팀(내선 3000)에 교체 요청을 하시면 됩니다. 잔량 10% 이하에서는 추가 알람이 발생하지 않으므로 운영팀의 정기 관리가 필요합니다. [FAQ §FAQ-004] [알람코드설명서 §AC-GAS-W-001]",
    },

    # ---------- Medium 8건 (다중 문서 결합) ----------
    {
        "voc_id": "VOC-2026-0009",
        "title": "TEMP-H-001 떴는데 조치 방법 알려주세요",
        "content": "THIN-CVD-02 CH-B에서 TEMP-H-001 발생. 현재 챔버 온도 335°C, recipe setpoint 310°C, recipe는 R-CVD-15입니다. 어떤 순서로 점검해야 하나요?",
        "user_role": "EQ_ENG", "user_id": "U0001",
        "equipment_id": "THIN-CVD-02", "alarm_code": "TEMP-H-001",
        "category": "조치 방법 문의", "priority": "HIGH",
        "created_at": "2026-05-14 09:30:00",
        "is_core": True, "difficulty": "medium", "expected_refusal": False,
        "source_document_hint": [
            "alarm_code_guide.md#sec-AC-TEMP-H-001",
            "troubleshooting_guide.md#sec-SOP-TEMP-001"
        ],
        "expected_key_points": [
            "TEMP-H-001 의미 (setpoint +20°C 초과)",
            "SOP-TEMP-001 1단계: 가스 공급 상태 확인",
            "2단계: 냉각수 유량/온도 확인",
            "3단계: 히터 출력 확인",
            "4단계: TC 응답 확인",
            "사전 안전: Toxic Gas 동시 검출 시 SOP-GAS-001 우선"
        ],
        "expected_answer": "TEMP-H-001은 챔버 온도가 setpoint +20°C를 초과한 High 알람입니다(현재 335°C는 setpoint 310°C +25°C). SOP-TEMP-001 절차에 따라 다음 순서로 점검하세요: ① 가스 공급 상태 확인(MFC 측정값 vs setpoint), ② 냉각수 유량/입출구 압력 확인, ③ 히터 출력 추이 확인(over-shoot 여부), ④ TC 응답 확인(메인/보조 TC 차이). 단계 1,2가 동시 fail이면 즉시 팀장 호출, 3·4로 원인 특정 불가면 벤더 escalation(SOP-ESC-001). 사전에 챔버 근처 가스 검출기 상태를 확인하여 Toxic Gas 동시 검출 시 SOP-GAS-001을 우선 진행하세요. [알람코드설명서 §AC-TEMP-H-001] [장애대응가이드 §SOP-TEMP-001]",
    },
    {
        "voc_id": "VOC-2026-0010",
        "title": "PRES-C-001 발생 — 조치 절차",
        "content": "ETCH-DRY-01에서 PRES-C-001이 발생하여 챔버가 hold 되었습니다. 조치 방법을 알려주세요.",
        "user_role": "EQ_ENG", "user_id": "U0002",
        "equipment_id": "ETCH-DRY-01", "alarm_code": "PRES-C-001",
        "category": "조치 방법 문의", "priority": "URGENT",
        "created_at": "2026-05-13 15:55:00",
        "is_core": True, "difficulty": "medium", "expected_refusal": False,
        "source_document_hint": [
            "alarm_code_guide.md#sec-AC-PRES-C-001",
            "troubleshooting_guide.md#sec-SOP-PRES-001"
        ],
        "expected_key_points": [
            "Critical은 수동 vent 금지", "터보 펌프 회전수 95% 이상 확인",
            "Throttle 위치 끝단 고착 여부",
            "가스 flow 합 +15% 초과 시 SOP-FLOW-001 병행",
            "Setpoint 변경 응답 테스트"
        ],
        "expected_answer": "PRES-C-001(챔버 압력 Critical) 발생 시 챔버가 자동 hold 됩니다. SOP-PRES-001 절차에 따라: ① Critical이므로 수동 vent 금지 — 펌프 상태부터 확인, ② 터보 펌프 회전수가 정상의 95% 이상인지 확인(미달 시 SOP-VAC-002 병행), ③ Throttle 밸브 위치가 0% 또는 100% 끝단에 고착되지 않았는지 확인, ④ 모든 MFC flow 합이 setpoint +15% 초과면 SOP-FLOW-001 병행, ⑤ Idle에서 setpoint 변경 응답 테스트로 회복 여부 검증. 펌프/throttle 하드웨어 이상이면 즉시 정비팀 호출, 4시간 내 재발 시 SOP-ESC-001 벤더 escalation. [알람코드설명서 §AC-PRES-C-001] [장애대응가이드 §SOP-PRES-001]",
    },
    {
        "voc_id": "VOC-2026-0011",
        "title": "RF-M-001 Matching 불량 — 어떻게 조정?",
        "content": "THIN-PVD-01 CH-A에서 RF-M-001 알람. Auto-tune이 되긴 하는데 reflected가 7% 정도 잔존합니다. 어떻게 조정하나요?",
        "user_role": "EQ_ENG", "user_id": "U0001",
        "equipment_id": "THIN-PVD-01", "alarm_code": "RF-M-001",
        "category": "조치 방법 문의", "priority": "HIGH",
        "created_at": "2026-05-13 11:00:00",
        "is_core": True, "difficulty": "medium", "expected_refusal": False,
        "source_document_hint": [
            "alarm_code_guide.md#sec-AC-RF-M-001",
            "troubleshooting_guide.md#sec-SOP-RF-002"
        ],
        "expected_key_points": [
            "RF-M-001: Auto-tune 후 reflected > 5% 잔존",
            "Auto-tune 재실행",
            "부하 변동 트리거(recipe 변경/chamber vent) 확인",
            "Tune cap 위치 끝단 도달 여부 확인",
            "Matcher reset 후 재실행",
            "수동 tune은 PROC_ENG 승인 — 24시간 내 PM 일정 반영 필수"
        ],
        "expected_answer": "RF-M-001은 Auto-tune 후 reflected가 5%를 초과해 잔존하는 Matching 불량 알람입니다. SOP-RF-002 절차로 ① Auto-tune 재실행(첫 시도로 해결 자주 됨), ② recipe 변경·chamber vent 후 첫 가동 등 부하 변동 트리거 확인, ③ Trend Chart에서 tune/load cap 위치가 끝단에 도달했는지 확인(끝단이면 cap 노후 의심), ④ Matcher 컨트롤러 reset 후 재실행, ⑤ 위 모두 실패 시 PROC_ENG 승인 하에 수동 tune 위치 적용 — 단, 일시 조치이므로 24시간 이내 PM 일정 반영 필수. Tune cap이 끝단에 도달했다면 정비팀에 Matcher 점검을 요청하세요. [알람코드설명서 §AC-RF-M-001] [장애대응가이드 §SOP-RF-002]",
    },
    {
        "voc_id": "VOC-2026-0012",
        "title": "IMP-HCI-01 VAC-C-001 — 진공 누설 대응",
        "content": "IMP-HCI-01에서 VAC-C-001 Critical 진공 누설 알람. base pressure 도달 실패. 조치 어떻게 하나요?",
        "user_role": "EQ_ENG", "user_id": "U0005",
        "equipment_id": "IMP-HCI-01", "alarm_code": "VAC-C-001",
        "category": "조치 방법 문의", "priority": "URGENT",
        "created_at": "2026-05-12 17:20:00",
        "is_core": True, "difficulty": "medium", "expected_refusal": False,
        "source_document_hint": [
            "alarm_code_guide.md#sec-AC-VAC-C-001",
            "troubleshooting_guide.md#sec-SOP-VAC-001"
        ],
        "expected_key_points": [
            "VAC-C-001: leak rate > 1e-5 Torr·L/s 또는 base pressure 도달 실패",
            "챔버 isolation",
            "Rate of Rise 측정",
            "누설 위치: viewport → door O-ring → feedthrough → gas line",
            "He leak test",
            "feedthrough 누설 시 PROC_ENG 승인 필수"
        ],
        "expected_answer": "VAC-C-001은 챔버 진공 누설 Critical(leak rate > 1e-5 Torr·L/s 또는 base pressure 도달 실패) 알람입니다. SOP-VAC-001 절차: ① 영향받은 챔버 inert gas로 격리, ② 5분간 Rate of Rise 측정 후 baseline과 비교, ③ 누설 위치 추정 순서 — viewport → 챔버 door O-ring → feedthrough → gas line, ④ 의심 부위 He leak test, ⑤ O-ring/viewport 등 부품 교체, ⑥ 펌프 다운 후 base pressure 도달 시간 검증. 3단계까지 위치 미확인 시 SOP-ESC-001 벤더 점검 요청, feedthrough 누설 확인 시 안전 절차상 PROC_ENG 승인 필수. [알람코드설명서 §AC-VAC-C-001] [장애대응가이드 §SOP-VAC-001]",
    },
    {
        "voc_id": "VOC-2026-0013",
        "title": "COMM-H-001 — EAP 통신 단절 조치",
        "content": "PHOTO-SCN-02에서 COMM-H-001 알람. 호스트 통신이 1분 이상 단절됐습니다. EAP 재시작은 제가 할 수 있나요?",
        "user_role": "EQ_ENG", "user_id": "U0003",
        "equipment_id": "PHOTO-SCN-02", "alarm_code": "COMM-H-001",
        "category": "조치 방법 문의", "priority": "HIGH",
        "created_at": "2026-05-11 14:00:00",
        "is_core": True, "difficulty": "medium", "expected_refusal": False,
        "source_document_hint": [
            "alarm_code_guide.md#sec-AC-COMM-H-001",
            "troubleshooting_guide.md#sec-SOP-COMM-001",
            "operation_policy.md#sec-POL-PERM-001"
        ],
        "expected_key_points": [
            "COMM-H-001: EAP-호스트 link 60초 이상 단절",
            "EAP 프로세스 상태 확인",
            "네트워크 ping 테스트",
            "EAP 재시작은 EQ_ENG 권한 가능",
            "수동 운영 모드 전환은 PROC_ENG 권한",
            "수동 운영 4시간 제한"
        ],
        "expected_answer": "COMM-H-001은 EAP-호스트 link가 60초 이상 단절된 상태입니다. SOP-COMM-001에 따라: ① 설비 EAP 컨트롤러 프로세스 상태 확인, ② ping 테스트로 네트워크 도달성 확인, ③ 네트워크 정상인데 SECS link만 끊긴 경우 EAP 프로세스 재시작 — EQ_ENG 권한으로 가능합니다, ④ 30분 이상 지연 예상 시 PROC_ENG 승인 하에 수동 운영 모드로 전환(최대 4시간 제한), ⑤ 복구 후 단절 기간의 알람·이벤트·데이터를 호스트에 강제 동기화. 네트워크 자체 이상이면 IT/CIM팀 호출, 수동 운영 4시간 초과 시 SOP-ESC-001. [장애대응가이드 §SOP-COMM-001] [운영정책 §POL-PERM-001]",
    },
    {
        "voc_id": "VOC-2026-0014",
        "title": "REC-H-001 — Recipe 다운로드 계속 실패",
        "content": "ETCH-DRY-03에서 recipe 다운로드가 3번 연속 실패해서 REC-H-001 알람이 떴습니다. 어떻게 해결하나요?",
        "user_role": "EQ_ENG", "user_id": "U0023",
        "equipment_id": "ETCH-DRY-03", "alarm_code": "REC-H-001",
        "category": "조치 방법 문의", "priority": "HIGH",
        "created_at": "2026-05-14 11:15:00",
        "is_core": True, "difficulty": "medium", "expected_refusal": False,
        "source_document_hint": [
            "alarm_code_guide.md#sec-AC-REC-H-001",
            "troubleshooting_guide.md#sec-SOP-REC-001"
        ],
        "expected_key_points": [
            "REC-H-001: MES → 설비 recipe 다운로드 3회 연속 실패",
            "checksum 비교",
            "권한 만료 확인",
            "수동 다운로드 3회 재시도",
            "PROC_ENG 재등록",
            "최후: CIM팀"
        ],
        "expected_answer": "REC-H-001은 MES → 설비 recipe 다운로드가 3회 연속 실패한 알람으로 checksum 불일치 또는 권한 만료가 주 원인입니다. SOP-REC-001 절차: ① MES 등록 recipe와 설비 수신 recipe의 checksum 비교, ② 다운로드 요청자(설비)의 MES 권한 유효성 확인(만료 시 POL-ACC-001), ③ 설비에서 수동 다운로드 재시도(3회 한정), ④ checksum 불일치 지속 시 PROC_ENG가 MES에서 recipe 재등록, ⑤ REC-W-001 동반 시 FAQ-008 수동 동기화. PROC_ENG 재등록 후에도 실패 시 CIM팀을 호출하세요. [알람코드설명서 §AC-REC-H-001] [장애대응가이드 §SOP-REC-001]",
    },
    {
        "voc_id": "VOC-2026-0015",
        "title": "GAS-H-001 — 가스 라인 누설 의심",
        "content": "DIFF-FUR-02에서 GAS-H-001 알람. MFC 입출력 압력 차가 이상하다고 합니다. 어떻게 점검하나요?",
        "user_role": "EQ_ENG", "user_id": "U0004",
        "equipment_id": "DIFF-FUR-02", "alarm_code": "GAS-H-001",
        "category": "조치 방법 문의", "priority": "HIGH",
        "created_at": "2026-05-13 19:00:00",
        "is_core": True, "difficulty": "medium", "expected_refusal": False,
        "source_document_hint": [
            "alarm_code_guide.md#sec-AC-GAS-H-001",
            "troubleshooting_guide.md#sec-SOP-GAS-002"
        ],
        "expected_key_points": [
            "GAS-H-001: 가스 라인 누설 의심",
            "Toxic Gas 동시 발생 시 즉시 SOP-GAS-001로 전환",
            "해당 가스 isolation",
            "MFC 입출력 압력 비교",
            "VCR fitting 점검",
            "He leak test"
        ],
        "expected_answer": "GAS-H-001은 MFC 입출력 압력 차와 flow 측정값 불일치로 인한 누설 의심 알람입니다. SOP-GAS-002 절차: ① 먼저 GAS-C-001(Toxic Gas) 동시 검출 여부 확인 — 동시 발생 시 즉시 SOP-GAS-001로 전환하여 EHS 절차 우선, ② manual valve 또는 EAP에서 해당 가스 라인 isolation, ③ Trend Chart로 MFC 입력압/출력압 추이 비교하여 비정상 차이 구간 확인, ④ 의심 VCR fitting을 시각/촉각으로 점검(부식·균열), ⑤ He 분사 후 RGA로 leak 신호 확인, ⑥ 부품 교체 후 누설 재측정. 누설 위치 미확인 시 SOP-ESC-001 벤더 escalation. [알람코드설명서 §AC-GAS-H-001] [장애대응가이드 §SOP-GAS-002]",
    },
    {
        "voc_id": "VOC-2026-0016",
        "title": "DOSE-C-001 — Critical Dose 이상 발생",
        "content": "IMP-HCI-02에서 DOSE-C-001이 발생했습니다. wafer hold 처리는 자동으로 되는 건가요? 다음 단계는?",
        "user_role": "PROC_ENG", "user_id": "U0011",
        "equipment_id": "IMP-HCI-02", "alarm_code": "DOSE-C-001",
        "category": "조치 방법 문의", "priority": "URGENT",
        "created_at": "2026-05-12 22:30:00",
        "is_core": True, "difficulty": "medium", "expected_refusal": False,
        "source_document_hint": [
            "alarm_code_guide.md#sec-AC-DOSE-C-001",
            "troubleshooting_guide.md#sec-SOP-DOSE-001"
        ],
        "expected_key_points": [
            "DOSE-C-001: 측정 dose가 recipe spec의 ±5% 초과",
            "Critical은 자동 lot hold",
            "Faraday cup contamination 확인",
            "Beam profile 측정",
            "Calibration 절차 (PROC_ENG 승인)",
            "재측정 wafer 평가"
        ],
        "expected_answer": "DOSE-C-001은 측정 dose가 recipe spec의 ±5%를 초과한 Critical 알람으로, Critical severity에 따라 영향받은 wafer가 자동 lot hold 처리됩니다. SOP-DOSE-001 절차: ① 자동 lot hold 확인, ② Faraday cup 측정 raw signal noise level이 baseline +20% 이상이면 contamination 의심, ③ beam scan profile 균일도가 spec 이내인지 확인, ④ PROC_ENG 승인 하에 Faraday cup calibration recipe로 보정, ⑤ calibration 후 wafer 1매 재측정 평가. Contamination 확인 시 챔버 cleaning을 위해 정비팀, 5단계 회복 실패 시 SOP-ESC-001 벤더 escalation. [알람코드설명서 §AC-DOSE-C-001] [장애대응가이드 §SOP-DOSE-001]",
    },

    # ---------- Hard 6건 (알람코드 없이 증상만) ----------
    {
        "voc_id": "VOC-2026-0017",
        "title": "ETCH 챔버 온도가 자꾸 올라갑니다",
        "content": "ETCH-DRY-02 CH-A에서 공정 중 챔버 온도가 setpoint보다 점점 높아지는 현상이 어제부터 반복되고 있습니다. 알람이 뜬 적도 있고 안 뜬 적도 있습니다. 어떤 점부터 확인해야 하나요?",
        "user_role": "EQ_ENG", "user_id": "U0002",
        "equipment_id": "ETCH-DRY-02", "alarm_code": "",
        "category": "조치 방법 문의", "priority": "HIGH",
        "created_at": "2026-05-14 13:40:00",
        "is_core": True, "difficulty": "hard", "expected_refusal": False,
        "source_document_hint": [
            "alarm_code_guide.md#sec-AC-TEMP-H-001",
            "troubleshooting_guide.md#sec-SOP-TEMP-001"
        ],
        "expected_key_points": [
            "TEMP-H-001 가능성 시사 (setpoint +20°C)",
            "SOP-TEMP-001 순서: 가스 → 냉각수 → 히터 → TC",
            "산발적 발생은 점검 우선순위 1·2단계 권장"
        ],
        "expected_answer": "증상으로 보아 TEMP-H-001(챔버 과열 High, setpoint +20°C 초과) 알람과 가까운 패턴입니다. SOP-TEMP-001 절차에 따라 점검하시되, 산발적 발생이므로 먼저 ① 가스 공급 상태(MFC setpoint vs 실측), ② 냉각수 유량/입출구 온도차 추이를 우선 확인하세요. 이 두 항목이 정상이면 ③ 히터 출력 추이(over-shoot 패턴), ④ TC 응답(메인/보조 차이)을 확인합니다. 사전에 Toxic Gas 검출 여부 확인은 필수입니다. [알람코드설명서 §AC-TEMP-H-001] [장애대응가이드 §SOP-TEMP-001]",
    },
    {
        "voc_id": "VOC-2026-0018",
        "title": "퍼니스 zone마다 온도가 다르게 표시됩니다",
        "content": "DIFF-FUR-01의 5개 zone 온도가 평소와 다르게 zone 간 차이가 점점 벌어지고 있습니다. 어떻게 확인해야 하나요?",
        "user_role": "EQ_ENG", "user_id": "U0004",
        "equipment_id": "DIFF-FUR-01", "alarm_code": "",
        "category": "조치 방법 문의", "priority": "HIGH",
        "created_at": "2026-05-13 08:20:00",
        "is_core": True, "difficulty": "hard", "expected_refusal": False,
        "source_document_hint": [
            "alarm_code_guide.md#sec-AC-TEMP-H-002",
            "troubleshooting_guide.md#sec-SOP-TEMP-002"
        ],
        "expected_key_points": [
            "TEMP-H-002 가능성 (zone 간 > 8°C)",
            "SOP-TEMP-002 순서",
            "TC 교차 검증",
            "히터 단선 / 보온재 손상 가능성"
        ],
        "expected_answer": "다중 zone furnace의 zone 간 온도 편차가 8°C를 초과하면 TEMP-H-002(히터 Zone 편차 High) 알람이 발생할 가능성이 있습니다. SOP-TEMP-002에 따라: ① Trend Chart로 편차가 가장 큰 zone 식별, ② 해당 zone 메인/보조 TC 값 비교(5°C 초과 차이는 TC 자체 이상), ③ 인접 zone 대비 히터 출력 비정상 여부 확인(단선 시 0 또는 100% 고정), ④ 해당 zone 보온재의 PM 이력 확인(18개월 이상 시 손상 의심), ⑤ 단기 대책으로 PROC_ENG 승인 후 인접 zone 출력 보정, ⑥ 영구 조치는 정기 PM 시 TC/히터 교체. [알람코드설명서 §AC-TEMP-H-002] [장애대응가이드 §SOP-TEMP-002]",
    },
    {
        "voc_id": "VOC-2026-0019",
        "title": "Trend Chart가 비어 있고 데이터가 안 보입니다",
        "content": "PHOTO-CTR-01의 Trend Chart를 열었는데 차트 영역이 전부 비어 있습니다. 어떻게 해결해야 하나요?",
        "user_role": "OP", "user_id": "U0015",
        "equipment_id": "PHOTO-CTR-01", "alarm_code": "",
        "category": "Trend Chart 조회 오류", "priority": "NORMAL",
        "created_at": "2026-05-14 10:00:00",
        "is_core": True, "difficulty": "hard", "expected_refusal": False,
        "source_document_hint": [
            "system_user_manual.md#sec-SM-TRD-002",
            "faq.md#sec-FAQ-002"
        ],
        "expected_key_points": [
            "흔한 원인 3가지: 수집 누락 / DAQ 이슈 / 기간 과도",
            "다른 SVID 확인",
            "통신 단절 시기 확인 (COMM-W-001/002)",
            "데이터 누락이면 VOC 등록"
        ],
        "expected_answer": "Trend Chart가 비어 있을 때의 일반 원인은 ① 선택 기간 동안 해당 SVID의 수집 데이터가 없음, ② 데이터 수집 시스템(DAQ) 측 이슈, ③ 기간이 너무 길어 timeout — 의 세 가지입니다. 확인 순서는 a) 같은 설비의 다른 SVID도 비어 있는지 확인 — 모두 비어 있으면 통신 단절 시기(COMM-W-001/002) 의심, b) 같은 SVID가 다른 설비에서도 비어 있으면 DAQ 측 이슈, c) 기간을 7일 이내로 줄여 재조회. 모두 정상인데도 누락된 경우 VOC `데이터 누락 문의` 카테고리로 등록해 주세요. [시스템사용매뉴얼 §SM-TRD-002] [FAQ §FAQ-002]",
    },
    {
        "voc_id": "VOC-2026-0020",
        "title": "임계치 변경하려고 하는데 권한이 없다고 나옵니다",
        "content": "TEMP-H-001 알람의 임계치를 변경하려고 신청하고 싶은데 화면에서 권한 부족 메시지가 뜹니다. 저는 설비 엔지니어입니다.",
        "user_role": "EQ_ENG", "user_id": "U0002",
        "equipment_id": "", "alarm_code": "",
        "category": "권한 문제", "priority": "NORMAL",
        "created_at": "2026-05-12 16:10:00",
        "is_core": True, "difficulty": "hard", "expected_refusal": False,
        "source_document_hint": [
            "operation_policy.md#sec-POL-PERM-002",
            "operation_policy.md#sec-POL-CHG-001",
            "faq.md#sec-FAQ-006"
        ],
        "expected_key_points": [
            "신청은 EQ_ENG 가능, 승인은 PROC_ENG",
            "임계치 변경 신청 절차 (양식)",
            "정량적 근거 필수",
            "POL-CHG-001 절차"
        ],
        "expected_answer": "임계치 변경 권한 정책에 따르면 신청은 EQ_ENG도 가능합니다(POL-PERM-002). 권한 부족 메시지는 ① 단순 화면 새로고침 누락 또는 ② 본인 계정의 역할이 시스템에 EQ_ENG로 등록되지 않은 경우일 수 있습니다. 화면 새로고침 후에도 같은 메시지면 본인 프로필에서 등록된 역할을 확인하고, 잘못된 경우 POL-ACC-001에 따라 부서장 승인 후 권한 변경 신청을 진행하세요. 변경 신청 시 정량적 근거(최근 30일 false alarm rate 등)와 영향 평가는 필수이며, 자세한 양식·승인 단계는 POL-CHG-001을 참조하세요. [운영정책 §POL-PERM-002] [운영정책 §POL-CHG-001] [FAQ §FAQ-006]",
    },
    {
        "voc_id": "VOC-2026-0021",
        "title": "야간에 Critical 알람 뜨면 어디로 연락해야 하나요",
        "content": "야간조 운영입니다. Critical 알람이 발생했을 때 누구에게 먼저 연락해야 하나요? 본인이 임시 운영 결정도 할 수 있나요?",
        "user_role": "OP", "user_id": "U0025",
        "equipment_id": "", "alarm_code": "",
        "category": "조치 방법 문의", "priority": "NORMAL",
        "created_at": "2026-05-11 23:50:00",
        "is_core": True, "difficulty": "hard", "expected_refusal": False,
        "source_document_hint": [
            "operation_policy.md#sec-POL-NIGHT-001",
            "troubleshooting_guide.md#sec-SOP-ESC-002",
            "faq.md#sec-FAQ-010"
        ],
        "expected_key_points": [
            "자동 호출 트리: EQ_ENG → 팀장 → 공정 PM → 벤더 Tier 2",
            "Critical SLA 5분 이내 1차 응답",
            "임시 운영 결정은 공정 PM 이상",
            "EHS 알람은 EHS 핫라인 별도"
        ],
        "expected_answer": "야간/주말 Critical 알람은 자동 호출 트리에 따라 호출이 진행됩니다(POL-NIGHT-001). 트리 순서는 ① 야간조 EQ_ENG(즉시) → ② 팀장(15분 내 응답 없으면) → ③ 공정 PM → ④ 벤더 Tier 2입니다. Critical 1차 응답 SLA는 5분 이내입니다. 임시 운영/라인 정지 결정 권한은 공정 PM 이상이므로 OP 또는 EQ_ENG가 단독으로 결정할 수는 없습니다 — 다만 인명 안전과 관련된 GAS-C-001 등은 SOP-GAS-001을 우선하며 EHS 핫라인(내선 9119)으로도 별도 신고가 필요합니다. 사후 보고는 정규시간 시작 후 4시간 이내 작성합니다. [운영정책 §POL-NIGHT-001] [장애대응가이드 §SOP-ESC-002] [FAQ §FAQ-010]",
    },
    {
        "voc_id": "VOC-2026-0022",
        "title": "VOC 등록한지 6시간 지났는데 담당자가 안 보입니다",
        "content": "어제 NORMAL 우선순위로 VOC를 등록했는데 6시간이 지나도록 담당자가 안 보이고 상태가 OPEN 그대로입니다. 정상인가요?",
        "user_role": "FIELD", "user_id": "U0019",
        "equipment_id": "", "alarm_code": "",
        "category": "VOC 처리 상태 문의", "priority": "NORMAL",
        "created_at": "2026-05-14 09:00:00",
        "is_core": True, "difficulty": "hard", "expected_refusal": False,
        "source_document_hint": [
            "operation_policy.md#sec-POL-SLA-001",
            "faq.md#sec-FAQ-005"
        ],
        "expected_key_points": [
            "NORMAL 1차 응답 SLA: 4시간",
            "6시간이면 SLA 초과 — 자동 escalation 알림 발송됨",
            "카테고리에 따라 수동 배정 — 최대 영업일 1일",
            "24시간 초과 시 본인이 팀장에게 통보"
        ],
        "expected_answer": "NORMAL 우선순위 VOC의 1차 응답 SLA는 4시간입니다(POL-SLA-001). 6시간이 지났다면 SLA를 초과한 상태이며 시스템이 자동으로 팀장에게 escalation 알림을 발송했을 것입니다. 일부 카테고리는 자동 배정 룰이 없어 운영 관리자의 수동 배정이 필요해 최대 영업일 1일이 소요될 수 있으므로 그 범위 내에서는 정상 동작일 수 있습니다. 24시간 이상 미배정 시에는 본인이 직접 팀장에게 통보하는 것을 권장합니다. [운영정책 §POL-SLA-001] [FAQ §FAQ-005]",
    },

    # ---------- Edge 4건 (KB 근거 부족 — "근거 없음") ----------
    {
        "voc_id": "VOC-2026-0023",
        "title": "RF Matcher tune cap fine-tuning 추천값",
        "content": "ETCH-DRY-02 CH-B의 RF Matcher tune cap 위치 fine-tuning을 위한 추천값이나 일반적인 최적 범위를 알려주세요. 현재 reflected가 6% 정도 잔존합니다.",
        "user_role": "EQ_ENG", "user_id": "U0002",
        "equipment_id": "ETCH-DRY-02", "alarm_code": "",
        "category": "조치 방법 문의", "priority": "NORMAL",
        "created_at": "2026-05-13 14:00:00",
        "is_core": True, "difficulty": "edge", "expected_refusal": True,
        "source_document_hint": [
            "operation_policy.md#sec-POL-SCOPE-001",
            "operation_policy.md#sec-POL-ESC-002",
            "troubleshooting_guide.md#sec-SOP-ESC-001"
        ],
        "expected_key_points": [
            "Tune cap 추천값은 KB Out-of-Scope (벤더 내부 파라미터)",
            "명시적 거절 — '근거를 찾을 수 없습니다'",
            "SOP-RF-002 일반 절차 안내 가능",
            "벤더 escalation 경로 안내"
        ],
        "expected_answer": "현재 지식베이스에서 근거를 찾을 수 없습니다. RF Matcher tune/load cap의 fine-tuning 추천값은 벤더 내부 파라미터에 해당하며, 본 시스템의 KB 범위 밖입니다(POL-SCOPE-001). 다만 RF Matching 불량의 일반 절차는 SOP-RF-002를 참조하실 수 있으며(Auto-tune 재실행, 부하 변동 확인, Matcher reset 등), 그 절차로 해결되지 않으면 SOP-ESC-001에 따라 벤더 기술지원 티켓을 발행하시면 됩니다. [운영정책 §POL-SCOPE-001] [운영정책 §POL-ESC-002]",
    },
    {
        "voc_id": "VOC-2026-0024",
        "title": "HCI Implanter Beam Profile 최적화 파라미터",
        "content": "IMP-HCI-01의 beam scan profile을 최적화하려고 합니다. 일반적인 최적 beam current와 scan speed의 조합을 알려주세요.",
        "user_role": "PROC_ENG", "user_id": "U0011",
        "equipment_id": "IMP-HCI-01", "alarm_code": "",
        "category": "조치 방법 문의", "priority": "NORMAL",
        "created_at": "2026-05-12 11:25:00",
        "is_core": True, "difficulty": "edge", "expected_refusal": True,
        "source_document_hint": [
            "operation_policy.md#sec-POL-SCOPE-001",
            "operation_policy.md#sec-POL-ESC-002"
        ],
        "expected_key_points": [
            "Beam profile 최적화 파라미터는 Out-of-Scope (벤더+recipe 영역)",
            "명시적 거절",
            "벤더/공정팀 escalation 안내"
        ],
        "expected_answer": "현재 지식베이스에서 근거를 찾을 수 없습니다. Implanter beam profile의 구체적인 최적 파라미터(beam current/scan speed 등) 추천값은 벤더 내부 파라미터 및 recipe 최적화 영역에 해당하며 본 시스템의 KB 범위 밖입니다(POL-SCOPE-001). 일반적인 dose 측정 이상 대응 절차는 SOP-DOSE-001에서 다루고 있으니 참고하시고, recipe 최적화 추천값은 공정팀 또는 SOP-ESC-001에 따른 벤더 기술지원 채널로 문의하시는 것이 정확합니다. [운영정책 §POL-SCOPE-001]",
    },
    {
        "voc_id": "VOC-2026-0025",
        "title": "TEMP-W-001 알람의 SOP가 어디 있나요",
        "content": "THIN-CVD-03에서 TEMP-W-001 Warning이 자주 뜨고 있습니다. 이 알람의 표준 조치 절차(SOP)를 알려주세요.",
        "user_role": "EQ_ENG", "user_id": "U0001",
        "equipment_id": "THIN-CVD-03", "alarm_code": "TEMP-W-001",
        "category": "조치 방법 문의", "priority": "LOW",
        "created_at": "2026-05-11 17:30:00",
        "is_core": True, "difficulty": "edge", "expected_refusal": True,
        "source_document_hint": [
            "alarm_code_guide.md#sec-AC-TEMP-W-001",
            "troubleshooting_guide.md#sec-SOP-TEMP-002"
        ],
        "expected_key_points": [
            "TEMP-W-001은 별도 SOP 미정의 (KB orphan)",
            "Idle 자연 냉각으로 정상 동작 범위",
            "반복 또는 다음 Lot 도달 지연 시 SOP-TEMP-002 참조 권장"
        ],
        "expected_answer": "TEMP-W-001(챔버 저온 Warning)에는 별도 표준 SOP가 정의되어 있지 않습니다. 본 알람은 Idle 상태에서의 자연 냉각에 가까운 경고성 알람으로 분류되어 있어 KB에 SOP가 매핑되지 않은 케이스입니다. 다만 동일 Warning이 반복적으로 발생하거나, 다음 Lot 시작 시 가열 도달 지연이 함께 보고되면 SOP-TEMP-002(가열 속도 이상)를 참조하여 히터 출력을 점검하시는 것이 권장됩니다. 추가 진단이 필요하면 VOC 본문에 발생 빈도와 다음 Lot 도달 시간을 함께 기록해 주세요. [알람코드설명서 §AC-TEMP-W-001]",
    },
    {
        "voc_id": "VOC-2026-0026",
        "title": "MES에서 recipe를 어떻게 등록하나요",
        "content": "신규 recipe를 MES 시스템에 등록하려고 하는데 등록 절차가 어떻게 되나요? FDC 시스템에서 등록 가능한가요?",
        "user_role": "PROC_ENG", "user_id": "U0008",
        "equipment_id": "", "alarm_code": "",
        "category": "조치 방법 문의", "priority": "NORMAL",
        "created_at": "2026-05-14 15:30:00",
        "is_core": True, "difficulty": "edge", "expected_refusal": True,
        "source_document_hint": ["operation_policy.md#sec-POL-SCOPE-001"],
        "expected_key_points": [
            "MES 시스템 사용법은 Out-of-Scope",
            "본 시스템은 FDC 전용",
            "MES 매뉴얼 별도 참조 안내"
        ],
        "expected_answer": "현재 지식베이스에서 근거를 찾을 수 없습니다. MES 시스템에서의 recipe 등록 절차는 사내 다른 시스템의 사용법에 해당하며 본 FDC-Monitoring AI System의 KB 범위 밖입니다(POL-SCOPE-001). 본 시스템에서는 등록된 recipe의 다운로드 실패(REC-H-001) 등 운영 중 발생하는 이슈를 다루며, recipe 등록 자체는 MES 시스템 매뉴얼 또는 CIM팀에 문의해 주세요. [운영정책 §POL-SCOPE-001]",
    },

    # ---------- Trap 2건 (존재하지 않는 코드/설비) ----------
    {
        "voc_id": "VOC-2026-0027",
        "title": "TEMP-Z-999 알람이 떴습니다",
        "content": "오늘 오전 대시보드에 TEMP-Z-999라는 알람이 떴습니다. 무엇을 의미하는 알람인가요? 어떻게 조치해야 하나요?",
        "user_role": "OP", "user_id": "U0017",
        "equipment_id": "", "alarm_code": "TEMP-Z-999",
        "category": "알람 코드 의미 문의", "priority": "NORMAL",
        "created_at": "2026-05-14 11:00:00",
        "is_core": True, "difficulty": "trap", "expected_refusal": True,
        "source_document_hint": ["operation_policy.md#sec-POL-SCOPE-001"],
        "expected_key_points": [
            "TEMP-Z-999는 등록된 알람코드가 아님",
            "Severity Z는 정의되지 않음 (정의: C/H/M/W/I)",
            "명시적으로 '존재하지 않는다'를 명시",
            "올바른 코드 재확인 요청"
        ],
        "expected_answer": "현재 지식베이스에서 근거를 찾을 수 없습니다. TEMP-Z-999는 등록된 알람 코드가 아닙니다. 본 시스템의 Severity 코드는 C(Critical) / H(High) / M(Medium) / W(Warning) / I(Info) 5가지로 정의되어 있어 'Z'라는 severity는 존재하지 않습니다. 대시보드 표시를 다시 한 번 확인해 주시고, 정확한 알람 코드 또는 발생 화면 캡처를 첨부하여 VOC를 다시 등록해 주세요. 만약 시스템 표시 자체가 잘못된 경우라면 시스템 접속 오류 카테고리로 VOC 등록해 주시기 바랍니다.",
    },
    {
        "voc_id": "VOC-2026-0028",
        "title": "ETCH-DRY-99 PRES-C-001 발생",
        "content": "ETCH-DRY-99 설비에서 PRES-C-001 Critical 알람 발생했습니다. 빠른 조치 부탁드립니다.",
        "user_role": "OP", "user_id": "U0016",
        "equipment_id": "ETCH-DRY-99", "alarm_code": "PRES-C-001",
        "category": "조치 방법 문의", "priority": "URGENT",
        "created_at": "2026-05-13 20:00:00",
        "is_core": True, "difficulty": "trap", "expected_refusal": True,
        "source_document_hint": ["operation_policy.md#sec-POL-SCOPE-001"],
        "expected_key_points": [
            "ETCH-DRY-99는 등록된 설비가 아님 (ETCH-DRY는 01/02/03만 존재)",
            "설비 ID 재확인 요청",
            "PRES-C-001 자체는 유효 코드 (SOP-PRES-001) — 단, 설비 미존재로 답변 불가",
        ],
        "expected_answer": "현재 지식베이스에서 근거를 찾을 수 없습니다. ETCH-DRY-99는 등록된 설비가 아닙니다 — 본 시스템에 등록된 ETCH-DRY 설비는 ETCH-DRY-01, ETCH-DRY-02, ETCH-DRY-03 세 대입니다. 정확한 설비 ID를 다시 확인하여 VOC를 재등록해 주세요. 참고로 PRES-C-001(챔버 압력 Critical) 자체는 유효한 알람 코드이며, 설비가 확인되면 SOP-PRES-001에 따른 표준 조치 절차를 안내해 드릴 수 있습니다.",
    },

    # ---------- Multi-turn 2건 ----------
    {
        "voc_id": "VOC-2026-0029",
        "title": "알람이 자꾸 떠요",
        "content": "요즘 알람이 너무 자주 뜹니다. 왜 그런 건가요?",
        "user_role": "FIELD", "user_id": "U0020",
        "equipment_id": "", "alarm_code": "",
        "category": "알람 원인 문의", "priority": "NORMAL",
        "created_at": "2026-05-14 14:00:00",
        "is_core": True, "difficulty": "multi_turn", "expected_refusal": False,
        "source_document_hint": ["system_user_manual.md#sec-SM-VOC-001"],
        "expected_key_points": [
            "정보 부족 — 명확화 질문 필요",
            "필요 정보: 설비 ID, 알람 코드, 발생 시점/빈도",
            "답변보다 질문 우선",
            "추가 확인 질문 슬롯 활용"
        ],
        "expected_clarification": [
            "어느 설비에서 발생하나요? (예: THIN-CVD-02)",
            "알람 코드는 무엇입니까? (예: TEMP-H-001)",
            "언제부터 발생했고 시간당 몇 회 정도 발생하나요?",
        ],
        "expected_answer": "현재 정보만으로는 정확한 답변이 어렵습니다. 정확한 진단을 위해 다음을 확인해 주세요. ① 어느 설비에서 발생하나요? (예: THIN-CVD-02) ② 어떤 알람 코드가 표시되나요? (예: TEMP-H-001, COMM-W-001 등) ③ 언제부터 발생했고, 시간당 또는 일별 몇 회 정도 발생하나요? 위 정보를 보내주시면 알람 코드 의미와 표준 SOP를 안내해 드리겠습니다. [시스템사용매뉴얼 §SM-VOC-001]",
    },
    {
        "voc_id": "VOC-2026-0030",
        "title": "어제 등록한 VOC 상태 확인하고 싶어요",
        "content": "어제 등록한 VOC가 처리됐는지 확인하고 싶습니다. 어디서 볼 수 있나요?",
        "user_role": "OP", "user_id": "U0014",
        "equipment_id": "", "alarm_code": "",
        "category": "VOC 처리 상태 문의", "priority": "LOW",
        "created_at": "2026-05-14 17:20:00",
        "is_core": True, "difficulty": "multi_turn", "expected_refusal": False,
        "source_document_hint": [
            "system_user_manual.md#sec-SM-VOC-002",
            "operation_policy.md#sec-POL-SLA-001"
        ],
        "expected_key_points": [
            "VOC ID 또는 본인 메뉴 안내",
            "추가 확인: 정확한 VOC ID",
            "상태 단계 의미 설명 (OPEN/IN_PROGRESS/RESOLVED/CLOSED)"
        ],
        "expected_clarification": [
            "VOC ID를 알고 계신가요? (예: VOC-2026-0042)",
        ],
        "expected_answer": "본인이 등록한 VOC는 좌측 메뉴 `VOC → 내 VOC` 에서 모두 조회할 수 있습니다(SM-VOC-002). 상태는 OPEN(담당자 미배정) → IN_PROGRESS(처리 중) → RESOLVED(조치 완료, 등록자 확인 대기) → CLOSED 순서로 변경됩니다. 특정 VOC ID(예: VOC-2026-0042)를 알려주시면 해당 건의 처리 상태와 SLA 적용 정보(POL-SLA-001)를 함께 확인해 드릴 수 있습니다. [시스템사용매뉴얼 §SM-VOC-002]",
    },
]


# =============================================================================
# 일반 70건 — 페르소나·상황·시간·사전 시도를 조합한 다양·장문 양산
# -----------------------------------------------------------------------------
# 길이 혼합 분포: short(~10%) / medium(~70%) / long(~20%)
# =============================================================================

PERSONA_OPENERS = {
    "EQ_ENG": [
        "{eq} 담당 EQ 엔지니어입니다.",
        "오늘 {eq} 정기 점검 중 발견했습니다.",
        "{eq} {chamber} 가동 모니터링하다가 확인했습니다.",
        "방금 {eq}에서 알람 통보를 받고 즉시 확인했습니다.",
    ],
    "PROC_ENG": [
        "공정팀 PROC_ENG입니다. {eq} 관련해서 확인 요청드립니다.",
        "오늘 {eq}의 공정 트렌드를 보다가 이상점을 발견했습니다.",
        "수율 회의 준비 중 {eq} 데이터에서 의문점이 생겼습니다.",
        "임계치 검토 차원에서 {eq}의 최근 알람 분포를 보고 있습니다.",
    ],
    "OP": [
        "{shift}조 운영입니다. {eq} 가동 중 발생했습니다.",
        "당직 중 {eq} 콘솔에 알람이 떠서 보고드립니다.",
        "방금 인수인계 받았는데 {eq} 상태가 이상합니다.",
        "{eq} 라인 책임 운영자입니다. 확인 부탁드립니다.",
    ],
    "FIELD": [
        "현장 점검 중인 FIELD입니다. {eq}에서 이상 징후가 보입니다.",
        "{eq} 주변 정기 순회 중 발견했습니다.",
        "센서/배관 청소 작업 중 {eq}에서 평소와 다른 점이 보였습니다.",
        "{eq} 현장 근접 점검 중 알람 표시를 확인했습니다.",
    ],
}

TIME_PHRASES = [
    "오늘 오전 9시경부터", "어제 야간조 인수인계 직후", "방금 직전 lot 종료 후",
    "두 시간 전쯤부터", "오전 PM 작업 직후", "점심시간 직전부터",
    "어제부터 간헐적으로", "지난 주말 PM 이후",
]

LOT_PHRASES = [
    "현재 R-{type}-{n:02d} recipe로 lot 진행 중이며,",
    "LOT-20260514-{n:03d} 가동 중에 발생했고,",
    "직전 PM 직후 첫 lot이라 환경 영향이 의심되는데,",
    "동일 recipe로 어제까지는 정상이었는데",
    "다음 lot 시작 전에 해소되어야 하는 상황이라",
    "오늘 야간 lot 배정이 이미 잡혀 있어",
]

TEAM_PHRASES = [
    "팀장님께는 우선 1차 보고드린 상태이며",
    "옆 챔버 담당 동료도 비슷한 알람을 봤다고 하는데",
    "야간조 인수인계 노트에도 같은 코드가 한 번 적혀 있어서",
    "공정팀에서는 임계치 조정 검토 중이라고 하시고",
    "장비 벤더 측에 사전 문의는 아직 안 드린 상태이고",
    "어제 PM 보고서에 비슷한 증상이 기록되어 있었습니다.",
]

ATTEMPT_PHRASES_GENERIC = [
    "Trend Chart에서 최근 24시간 추이를 확인해 봤는데 명확한 spike는 없어 보였고,",
    "EAP 재시작은 한 번 시도해 봤지만 동일 증상이 다시 나타났으며,",
    "Recipe 파라미터는 정상 범위였고,",
    "동일 카테고리의 다른 설비는 정상 가동 중이라",
    "관련 알람 이력을 조회해 보니 비슷한 패턴이 일주일에 두세 번 반복되고 있고,",
    "운영 매뉴얼에 나와 있는 1차 조치는 이미 적용했는데 차도가 없어",
]

CLOSING_PHRASES = {
    "URGENT": [
        "Critical 단계라 즉시 답변 부탁드립니다.",
        "라인 정지 영향이 있어 빠른 회신이 필요합니다.",
        "5분 SLA 내 1차 응답 부탁드립니다.",
    ],
    "HIGH": [
        "다음 lot 시작 전까지 답변 부탁드립니다.",
        "오늘 안에는 회신 부탁드립니다.",
        "신속한 진단 의견 부탁드립니다.",
    ],
    "NORMAL": [
        "어떤 순서로 점검하면 좋을지 안내 부탁드립니다.",
        "관련 SOP가 있으면 알려주시면 감사하겠습니다.",
        "조치 방향과 추가로 확인할 항목이 있으면 알려주세요.",
    ],
    "LOW": [
        "여유 있을 때 회신 주시면 됩니다.",
        "근무시간 내 답변 부탁드립니다.",
        "참고용으로 자료만 안내해 주셔도 좋습니다.",
    ],
}

SHIFTS = ["A", "B", "C", "야간"]


def _pick_length_class(rng):
    r = rng.random()
    if r < 0.10:
        return "short"
    if r < 0.80:
        return "medium"
    return "long"


def _persona_opener(user, eq, rng):
    role = user["role"]
    pool = PERSONA_OPENERS.get(role, PERSONA_OPENERS["EQ_ENG"])
    chamber = ""
    if eq.get("chambers"):
        chambers = eq["chambers"].split("|")
        chamber = rng.choice(chambers) if chambers and chambers[0] else ""
    return rng.choice(pool).format(
        eq=eq["equipment_id"],
        chamber=chamber or "메인 챔버",
        shift=rng.choice(SHIFTS),
    )


def _lot_phrase(eq, rng):
    return rng.choice(LOT_PHRASES).format(
        type=eq["type"],
        n=rng.randint(1, 99),
    )


def _join_clauses(parts):
    # 빈 항목 제거 + 공백 정리 + 마침표 보장
    # 단, 쉼표로 끝나는 절은 다음 절과 자연스럽게 연결되도록 그대로 둠.
    cleaned = []
    for p in parts:
        if not p:
            continue
        p = p.strip()
        if p.endswith(","):
            cleaned.append(p)
            continue
        if not p.endswith((".", "?", "!", "다", "요")):
            p = p + "."
        cleaned.append(p)
    return " ".join(cleaned)


def _slice_core(core, length_class):
    """core 문자열을 문장 단위로 분할 후 length_class 에 맞춰 길이 조절."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", core.strip()) if s.strip()]
    if not sentences:
        return core
    if length_class == "short":
        return sentences[0]
    if length_class == "medium":
        return " ".join(sentences[:2]) if len(sentences) >= 2 else sentences[0]
    return " ".join(sentences)


def _expand_clauses(rng, length_class, opener, core, ask):
    """length_class 별로 보강 절을 삽입하여 본문 생성.

    목표 길이:
      short  ~ 60-100자  : opener + core_1sent + ask
      medium ~ 120-250자 : opener + time + core_1sent + ask
      long   ~ 250-400자 : opener + time + core_full + attempt + ask
    """
    if length_class == "short":
        return _join_clauses([opener, _slice_core(core, "short"), ask])
    if length_class == "medium":
        time_p = rng.choice(TIME_PHRASES) + " 발생한 상황이고,"
        return _join_clauses([opener, time_p, _slice_core(core, "short"), ask])
    # long — core 전체 + 보강 절 2개
    time_p = rng.choice(TIME_PHRASES) + " 발생한 상황이고,"
    attempt_p = rng.choice(ATTEMPT_PHRASES_GENERIC)
    return _join_clauses([opener, time_p, _slice_core(core, "long"), attempt_p, ask])


# -----------------------------------------------------------------------------
# 카테고리별 본문 빌더
# -----------------------------------------------------------------------------

def _build_alarm_cause(ac, eq, user, priority, rng, length_class):
    title = rng.choice([
        f"{ac['alarm_code']} 발생 — 원인이 궁금합니다",
        f"{eq['equipment_id']}에서 {ac['alarm_code']} 알람, 원인 가능성 문의",
        f"{ac['alarm_code']} 원인 진단 자문 요청 ({eq['equipment_id']})",
    ])
    opener = _persona_opener(user, eq, rng)
    causes_text = ac["typical_causes"].replace("|", ", ")
    core = (
        f"{ac['alarm_code']}({ac['name']}, severity {ac['severity']}) 알람이 떴는데, "
        f"임계치 조건은 '{ac['threshold_text']}' 로 알고 있습니다. "
        f"이 알람의 일반적 원인으로는 {causes_text} 정도가 알람코드설명서에 적혀 있는데, "
        f"우리 설비({eq['equipment_id']}, vendor {eq['vendor']}, {eq['install_year']}년 설치) "
        f"환경에서 어떤 원인이 가장 가능성 높은지 의견 주시면 좋겠습니다"
    )
    ask = rng.choice(CLOSING_PHRASES[priority])
    return title, _expand_clauses(rng, length_class, opener, core, ask)


def _build_alarm_action(ac, eq, user, priority, rng, length_class):
    title = rng.choice([
        f"{ac['alarm_code']} 발생, 조치 절차 안내 부탁드립니다",
        f"{eq['equipment_id']}에서 {ac['alarm_code']} — 어떤 순서로 점검하면 되나요",
        f"{ac['alarm_code']} 표준 대응 절차 확인 요청",
    ])
    opener = _persona_opener(user, eq, rng)
    sop = ac["related_sop_id"] or "관련 SOP"
    lot_p = _lot_phrase(eq, rng)
    core = (
        f"{ac['alarm_code']}({ac['name']}) 알람이 발생해서 챔버 상태를 확인했고, "
        f"{lot_p} 임계치 조건은 '{ac['threshold_text']}'이라 spec 이탈은 분명합니다. "
        f"관련 SOP는 {sop}으로 알고 있는데 단계별 점검 순서와, "
        f"단계별 fail 시 escalation 기준을 함께 안내해 주시면 좋겠습니다"
    )
    ask = rng.choice(CLOSING_PHRASES[priority])
    return title, _expand_clauses(rng, length_class, opener, core, ask)


def _build_alarm_meaning(ac, eq, user, priority, rng, length_class):
    title = rng.choice([
        f"{ac['alarm_code']} 알람의 의미가 궁금합니다",
        f"{ac['alarm_code']}은 어떤 상태에서 뜨는 알람인가요",
        f"{ac['alarm_code']} 정의 및 임계치 확인 요청",
    ])
    opener = _persona_opener(user, eq, rng)
    core = (
        f"{ac['alarm_code']} 알람이 처음 보는 코드라 정확한 의미를 알고 싶습니다. "
        f"카테고리는 {ac['category']}, severity는 {ac['severity']}로 표시되어 있는데 "
        f"이 알람이 정확히 어떤 상태에서 발생하는지, "
        f"임계치 조건과 우리 설비 타입({eq['type']})에 적용 가능한지 알람코드설명서 §{ac['section_id']}를 인용해서 알려주세요"
    )
    ask = rng.choice(CLOSING_PHRASES[priority])
    return title, _expand_clauses(rng, length_class, opener, core, ask)


def _build_trend_chart(eq, user, priority, rng, length_class):
    sub_issues = [
        ("일부 구간이 끊어져 보입니다", "특정 SVID 1~3개 구간이 결손되어 보이고 나머지는 정상이라"),
        ("차트가 통째로 비어 있습니다", "선택한 7일 기간 동안 모든 SVID에 데이터가 없어 보이고"),
        ("조회 시 timeout이 발생합니다", "조회를 누르면 30초 이상 대기 후 timeout이 뜨고 차트는 그려지지 않으며"),
        ("최신 데이터가 1시간 전 이후로 갱신되지 않습니다", "최신 timestamp가 1시간 이상 멈춰 있는 것으로 보이고"),
    ]
    sym_title, sym_desc = rng.choice(sub_issues)
    title = f"{eq['equipment_id']} Trend Chart {sym_title}"
    opener = _persona_opener(user, eq, rng)
    core = (
        f"{eq['equipment_id']} Trend Chart를 열어 봤는데 {sym_title}. {sym_desc} "
        f"수집 누락인지 DAQ 이슈인지 통신 단절(COMM-W-001/002) 영향인지 구분이 안 되어, "
        f"어떤 순서로 진단해야 하는지 시스템사용매뉴얼 §SM-TRD-002와 FAQ-002 내용을 토대로 안내 부탁드립니다"
    )
    ask = rng.choice(CLOSING_PHRASES[priority])
    return title, _expand_clauses(rng, length_class, opener, core, ask)


def _build_data_missing(eq, user, priority, rng, length_class):
    title = f"{eq['equipment_id']} 어제 일부 시간대 데이터 누락 확인 요청"
    opener = _persona_opener(user, eq, rng)
    core = (
        f"{eq['equipment_id']} 어제 자정~새벽 4시 구간의 sensor 데이터가 비어 있는 것 같습니다. "
        f"같은 시간대 다른 설비는 정상으로 보이는데 우리 설비만 누락된 상태라, "
        f"통신 단절 이벤트가 있었는지, DAQ 모듈 jitter(COMM-W-002)에 해당하는지, "
        f"아니면 해당 구간에 PM이 있었는지 확인 부탁드립니다"
    )
    ask = rng.choice(CLOSING_PHRASES[priority])
    return title, _expand_clauses(rng, length_class, opener, core, ask)


def _build_threshold(ac, user, priority, rng, length_class):
    delta = rng.choice(["+5%", "+10%", "-5%", "-10%"])
    title = rng.choice([
        f"{ac['alarm_code']} 임계치 {delta} 조정 검토 요청",
        f"{ac['alarm_code']} false alarm이 많아 임계치 재검토 필요",
        f"임계치 변경 신청 — {ac['alarm_code']}",
    ])
    opener = _persona_opener(user, {"equipment_id": "[해당 없음]", "type": ac["category"], "vendor": "-", "install_year": "-", "chambers": ""}, rng)
    core = (
        f"{ac['alarm_code']}({ac['name']}) 알람이 최근 30일 동안 빈번하게 발생하고 있는데, "
        f"실제 공정 영향이 미미한 false alarm 비율이 높은 것으로 분석됩니다. "
        f"현재 임계치 '{ac['threshold_text']}'를 {delta} 수준으로 조정 검토하고 싶습니다. "
        f"신청 절차(POL-CHG-001)와 승인 권한(POL-PERM-002), 필요한 정량 근거 양식을 안내 부탁드립니다"
    )
    ask = rng.choice(CLOSING_PHRASES[priority])
    return title, _expand_clauses(rng, length_class, opener, core, ask)


def _build_status_mismatch(eq, user, priority, rng, length_class):
    title = f"{eq['equipment_id']} 대시보드 상태와 실제 가동 상태 불일치"
    opener = _persona_opener(user, eq, rng)
    core = (
        f"{eq['equipment_id']} 대시보드에는 IDLE로 표시되어 있는데 현장 콘솔에서는 lot이 정상 진행 중입니다. "
        f"반대로 어제는 대시보드에 PRODUCTION으로 떠 있었는데 실제로는 PM 중이었던 적도 있어, "
        f"통신 단절(COMM-W-001/W-002) 또는 SECS/GEM 응답 지연(COMM-M-001) 영향으로 추정됩니다. "
        f"FAQ-003 안내와 함께 임시 조치와 재발 방지 대응을 알려주세요"
    )
    ask = rng.choice(CLOSING_PHRASES[priority])
    return title, _expand_clauses(rng, length_class, opener, core, ask)


def _build_permission(user, priority, rng, length_class):
    actions = [
        ("Trend CSV 다운로드 버튼이 비활성화되어 있습니다", "Trend CSV export"),
        ("Recipe 조회 메뉴 자체가 좌측 사이드바에 보이지 않습니다", "Recipe 조회"),
        ("알람 임계치 변경 신청 버튼을 눌렀더니 권한 부족이라고 합니다", "임계치 변경 신청"),
        ("VOC 일괄 처리 화면에 접근이 안 됩니다", "VOC 일괄 처리"),
    ]
    sym, action_label = rng.choice(actions)
    title = f"권한 부족 — {action_label}"
    opener = rng.choice([
        f"{user['name']}({user['role']}) 입니다.",
        f"{user['team']} 소속 {user['role']}입니다.",
        f"오늘 화면 조작 중 막혀서 문의드립니다.",
    ])
    core = (
        f"{sym}. 본인 역할은 {user['role']}이고 평소에는 동일 메뉴를 사용해 왔는데, "
        f"오늘부터 갑자기 권한 부족 메시지가 표시되는 상황입니다. "
        f"POL-PERM-001 권한 매트릭스 기준 본인 역할의 가능 작업과, "
        f"권한 변경/복구 신청 절차(POL-ACC-001)를 안내 부탁드립니다"
    )
    ask = rng.choice(CLOSING_PHRASES[priority])
    return title, _expand_clauses(rng, length_class, opener, core, ask)


def _build_login(user, priority, rng, length_class):
    issues = [
        ("로그인 시 권한 없음 메시지가 뜹니다", "ID/PW는 사내 SSO와 동기화되어 있다고 알고 있는데"),
        ("OTP 인증이 계속 실패합니다", "OTP 앱의 시간 동기화는 최근에 맞췄는데도"),
        ("계정이 잠겼다는 메시지가 표시됩니다", "비밀번호 변경 주기 알림은 받지 못했는데"),
    ]
    sym, hint = rng.choice(issues)
    title = f"시스템 접속 오류 — {sym}"
    opener = rng.choice([
        f"{user['team']} {user['name']}({user['role']}) 입니다.",
        f"오늘 출근 직후 접속이 안 되어 문의드립니다.",
        f"외부 출장에서 복귀 후 처음 접속을 시도 중입니다.",
    ])
    core = (
        f"{sym}. {hint} 동일 증상이 재현됩니다. "
        f"FAQ-001 권한·계정 관련 안내와 SM-LOGIN-001 매뉴얼을 기준으로 "
        f"본인 계정 상태 확인 절차와, 잠금 해제/재등록 신청 경로를 알려주세요"
    )
    ask = rng.choice(CLOSING_PHRASES[priority])
    return title, _expand_clauses(rng, length_class, opener, core, ask)


def _build_voc_status(user, priority, rng, length_class):
    days = rng.randint(1, 5)
    title = rng.choice([
        f"등록 후 {days}일 지난 VOC 처리 상태 문의",
        "내 VOC 화면에서 상태가 바뀌지 않습니다",
        "이전에 등록한 VOC들의 현재 단계 일괄 확인 요청",
    ])
    opener = rng.choice([
        f"{user['name']}({user['role']}) 입니다.",
        f"{user['team']} 소속 운영자입니다.",
        f"FDC 시스템 사용자 기준으로 문의드립니다.",
    ])
    core = (
        f"제가 {days}일 전 등록한 VOC가 아직 OPEN/IN_PROGRESS 단계에서 변동이 없어 보입니다. "
        f"POL-SLA-001 기준 NORMAL 우선순위의 1차 응답 시간은 4시간으로 알고 있는데, "
        f"현재 단계 의미(OPEN/IN_PROGRESS/RESOLVED/CLOSED), "
        f"단계별 표준 처리 시간, SLA 초과 시 자동 escalation 여부를 SM-VOC-002와 함께 안내해 주세요"
    )
    ask = rng.choice(CLOSING_PHRASES[priority])
    return title, _expand_clauses(rng, length_class, opener, core, ask)


CATEGORY_BUILDERS = {
    "알람 원인 문의": _build_alarm_cause,
    "조치 방법 문의": _build_alarm_action,
    "알람 코드 의미 문의": _build_alarm_meaning,
    "Trend Chart 조회 오류": _build_trend_chart,
    "데이터 누락 문의": _build_data_missing,
    "임계치 설정 문의": _build_threshold,
    "설비 상태 불일치": _build_status_mismatch,
    "권한 문제": _build_permission,
    "시스템 접속 오류": _build_login,
    "VOC 처리 상태 문의": _build_voc_status,
}

# 카테고리별로 alarm_code 필드가 본문에서 명시되는지 여부 (CSV 마스터 매칭용)
_CAT_USES_ALARM_CODE = {
    "알람 원인 문의", "조치 방법 문의", "알람 코드 의미 문의", "임계치 설정 문의",
}
_CAT_USES_EQUIPMENT = {
    "알람 원인 문의", "조치 방법 문의", "알람 코드 의미 문의",
    "Trend Chart 조회 오류", "데이터 누락 문의", "설비 상태 불일치",
}


def generate_filler_vocs(sot, equipment_rows, user_rows, alarm_code_rows, start_seq):
    """is_core=False 70건 생성 — 페르소나·시간·사전 시도 조합 + 길이 혼합 분포."""
    seed = sot["meta"]["generation_seed"] + 2
    rng = random.Random(seed)

    distribution = {
        "알람 원인 문의": 10, "조치 방법 문의": 7, "Trend Chart 조회 오류": 7,
        "데이터 누락 문의": 5, "임계치 설정 문의": 5, "설비 상태 불일치": 5,
        "권한 문제": 5, "시스템 접속 오류": 5, "알람 코드 의미 문의": 11,
        "VOC 처리 상태 문의": 10,
    }
    assert sum(distribution.values()) == 70, sum(distribution.values())

    start_date = datetime(2026, 4, 1)
    end_date = datetime(2026, 5, 15)
    duration = (end_date - start_date).days

    rows = []
    seq = start_seq
    for cat, count in distribution.items():
        builder = CATEGORY_BUILDERS[cat]
        for _ in range(count):
            user = rng.choice(user_rows)
            ac = rng.choice(alarm_code_rows)
            eq_candidates = [e for e in equipment_rows if eq_supports_alarm(e, ac)]
            eq = rng.choice(eq_candidates) if eq_candidates else rng.choice(equipment_rows)
            voc_id = f"VOC-2026-{seq:04d}"
            ts = start_date + timedelta(seconds=rng.randint(0, duration * 86400))
            length_class = _pick_length_class(rng)
            priority = rng.choices(
                ["LOW", "NORMAL", "HIGH", "URGENT"],
                weights=[0.20, 0.55, 0.20, 0.05],
            )[0]

            # builder 호출 — 카테고리에 따라 인자 분기
            if cat in {"알람 원인 문의", "조치 방법 문의", "알람 코드 의미 문의"}:
                title, content = builder(ac, eq, user, priority, rng, length_class)
            elif cat == "임계치 설정 문의":
                title, content = builder(ac, user, priority, rng, length_class)
            elif cat in {"Trend Chart 조회 오류", "데이터 누락 문의", "설비 상태 불일치"}:
                title, content = builder(eq, user, priority, rng, length_class)
            elif cat in {"권한 문제", "시스템 접속 오류"}:
                title, content = builder(user, priority, rng, length_class)
            elif cat == "VOC 처리 상태 문의":
                title, content = builder(user, priority, rng, length_class)
            else:
                title, content = builder(ac, eq, user, priority, rng, length_class)

            ac_code = ac["alarm_code"] if cat in _CAT_USES_ALARM_CODE else ""
            eq_id = eq["equipment_id"] if cat in _CAT_USES_EQUIPMENT else ""

            rows.append({
                "voc_id": voc_id,
                "title": title,
                "content": content,
                "user_role": user["role"],
                "user_id": user["user_id"],
                "equipment_id": eq_id,
                "alarm_code": ac_code,
                "category": cat,
                "priority": priority,
                "created_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "is_core": False,
                "difficulty": "filler",
                "expected_refusal": False,
                "source_document_hint": _filler_source_hint(cat, ac),
                "expected_key_points": [],
                "expected_answer": "",
            })
            seq += 1
    return rows


# =============================================================================
# Hard 확장 15건 — symptom_keywords + root_cause_tags 기반 자연어 VOC
#   - alarm_code 미명시 (증상만 서술)
#   - is_core=True, difficulty='hard'
# =============================================================================

HARD_EXTENSION_SPECS = [
    {
        "target_alarm": "TEMP-M-001",
        "target_sop": "SOP-TEMP-002",
        "title": "챔버 가열 ramp가 평소보다 한참 늦습니다",
        "symptom_paragraph": (
            "지난주까지는 idle에서 setpoint 도달까지 약 4분이면 충분했는데, "
            "오늘은 같은 recipe로도 6분 가까이 걸리고 있습니다. "
            "온도 ramp 그래프를 보면 초반 1/3 구간은 정상이고 후반에서 기울기가 눈에 띄게 완만해지며, "
            "히터 출력은 최대치 근처에서 더 올라가지 못하는 것처럼 보입니다. "
            "TC 응답이 늦어진 것 같다는 의심도 있어 보조 TC와 메인 TC 값을 비교해 봤는데 차이가 평소보다 큽니다."
        ),
        "key_points": [
            "TEMP-M-001 (가열 속도 이상, ramp ±15% 초과) 가능성",
            "원인: 히터 출력 저하 / TC 응답 지연",
            "SOP-TEMP-002 절차 안내",
        ],
        "primary_eq_types": ["CVD", "FUR", "RTP"],
    },
    {
        "target_alarm": "MECH-W-001",
        "target_sop": None,
        "title": "터보펌프 쪽에서 평소와 다른 진동이 느껴집니다",
        "symptom_paragraph": (
            "정비 순회 중 {eq} 터보펌프 하우징에서 평소에 못 느끼던 미세 진동이 손끝에 전해집니다. "
            "진동 RMS 추이를 보면 baseline 대비 1.5배 정도 올라와 있고, "
            "별도 알람은 아직 안 뜨고 있지만 베어링 마모 초기 증상 같은 느낌입니다. "
            "지금 단독 조치가 필요한 수준인지, 아니면 정기 PM 시까지 모니터링만 해도 되는지 판단을 부탁드립니다."
        ),
        "key_points": [
            "MECH-W-001 (진동 센서 경고) 가능성 — KB orphan",
            "원인: 베어링 마모 초기",
            "POL-SCOPE-001에 따라 KB 단독 조치 절차 없음 — Trend 모니터링 권장",
        ],
        "primary_eq_types": ["CVD", "PVD", "DRY", "POL"],
    },
    {
        "target_alarm": "RF-M-001",
        "target_sop": "SOP-RF-002",
        "title": "Auto-tune이 끝나도 반사파가 6~7% 정도 잔존합니다",
        "symptom_paragraph": (
            "{eq}에서 plasma ignition 후 Auto-tune이 완료된 시점에도 "
            "Reflected/Forward 비율이 6~7% 정도로 가라앉지 않고 있습니다. "
            "어제까지는 동일 recipe에서 1~2% 이내였는데, 오늘 첫 vent 후 가동부터 이 양상이 시작됐고, "
            "tune cap 위치 추이를 보니 점점 끝단 쪽으로 이동 중인 것이 마음에 걸립니다. "
            "수동 fine-tune으로 일시 회복은 되지만, 다음 lot에서 또 같은 증상이 재발할까 우려됩니다."
        ),
        "key_points": [
            "RF-M-001 (Auto-tune 후 reflected > 5% 잔존) 가능성",
            "원인: 부하 변동 / tune cap 노후",
            "SOP-RF-002 절차 안내",
        ],
        "primary_eq_types": ["CVD", "PVD", "DRY"],
    },
    {
        "target_alarm": "MECH-H-001",
        "target_sop": "SOP-MECH-001",
        "title": "EFEM 로봇이 wafer를 자주 놓칩니다",
        "symptom_paragraph": (
            "{eq}에서 오전부터 EFEM 로봇이 FOUP 슬롯 #14, #15 wafer를 잡았다가 transfer 중간에 흔들리는 현상이 두 번 있었습니다. "
            "한 번은 자동으로 retry가 성공했지만 한 번은 mapping 단계에서 wafer 인식 실패로 lot이 멈춰 있고, "
            "vacuum chuck 흡착 압력이 평소 대비 미세하게 떨어진 것으로 보입니다. "
            "wafer 회수 절차와, 같은 증상이 재발하지 않게 하기 위한 1차 점검 항목을 알려주세요."
        ),
        "key_points": [
            "MECH-H-001 (EFEM 로봇 wafer mapping/transfer 실패) 가능성",
            "원인: wafer 위치 이상 / vacuum chuck 흡착 불량",
            "SOP-MECH-001 절차 안내",
        ],
        "primary_eq_types": ["CVD", "PVD", "DRY", "SCN", "HCI", "MCI", "POL", "CLN", "MES", "INS"],
    },
    {
        "target_alarm": "MECH-M-001",
        "target_sop": "SOP-MECH-002",
        "title": "슬릿밸브 open/close 동작이 평소보다 느립니다",
        "symptom_paragraph": (
            "{eq}의 transfer chamber 슬릿밸브가 open/close 명령 후 정상 응답까지 0.7~0.8초 정도 걸리고 있습니다. "
            "spec은 ±0.5초인데 이미 spec을 살짝 넘어선 상태이고, "
            "공압 라인 게이지 압력이 평소 대비 약간 낮은 것 같습니다. "
            "센서 노후 가능성도 있을 것 같은데, 어떤 순서로 점검해야 하는지 안내 부탁드립니다."
        ),
        "key_points": [
            "MECH-M-001 (슬릿밸브 동작 이상) 가능성",
            "원인: 공압 라인 압력 저하 / 센서 노후",
            "SOP-MECH-002 절차 안내",
        ],
        "primary_eq_types": ["CVD", "PVD", "DRY", "HCI", "MCI"],
    },
    {
        "target_alarm": "VAC-H-001",
        "target_sop": "SOP-VAC-001",
        "title": "base pressure가 목표 1e-6 Torr에 도달하지 못합니다",
        "symptom_paragraph": (
            "{eq} 오늘 첫 가동에서 base pressure가 5e-6 Torr 부근에서 더 떨어지지 않고 머물러 있습니다. "
            "어제 PM 후 첫 가동이라 chamber outgassing 영향일 가능성도 생각해 보고 있는데, "
            "터보펌프 회전수는 정상으로 보입니다. "
            "현재 상태로 lot 시작해도 되는지, 아니면 추가 baking이 필요한지 판단해 주세요."
        ),
        "key_points": [
            "VAC-H-001 (진공도 미달 High, base pressure > 5e-6 Torr) 가능성",
            "원인: 펌프 성능 저하 / 챔버 outgassing",
            "SOP-VAC-001 절차 안내",
        ],
        "primary_eq_types": ["CVD", "PVD", "DRY", "HCI", "MCI"],
    },
    {
        "target_alarm": "VAC-W-001",
        "target_sop": "SOP-VAC-002",
        "title": "vent 후 base pressure 회복까지 시간이 점점 길어집니다",
        "symptom_paragraph": (
            "{eq}에서 vent → pump down → base pressure 도달까지의 시간이 baseline 대비 20% 정도 길어진 추세가 일주일째 이어지고 있습니다. "
            "회복 시간 trend가 우상향으로 천천히 올라가고 있어 펌프 성능 저하 초기 징후가 아닐까 의심됩니다. "
            "정기 PM은 한 달 뒤로 잡혀 있는데, 그때까지 모니터링만 해도 되는지 확인 부탁드립니다."
        ),
        "key_points": [
            "VAC-W-001 (진공 회복 지연) 가능성",
            "원인: 펌프 성능 저하 초기",
            "SOP-VAC-002 절차 안내 (모니터링 및 PM 일정 검토)",
        ],
        "primary_eq_types": ["CVD", "PVD", "DRY"],
    },
    {
        "target_alarm": "COMM-W-001",
        "target_sop": "SOP-COMM-001",
        "title": "T3 timeout이 하루 5~6회 발생합니다 (자동 복구는 됨)",
        "symptom_paragraph": (
            "{eq}와 호스트 간 SECS 통신에서 T3 timeout이 하루 5~6회 발생하고 있습니다. "
            "매번 자동 재시도로 복구는 되고 있어 큰 문제는 없지만, "
            "이전 주까지는 하루 1회 정도였던 것이 갑자기 늘어난 것이 신경 쓰입니다. "
            "네트워크 미세 지연 이상의 원인이 있는지, 별도 조치가 필요한지 확인 부탁드립니다."
        ),
        "key_points": [
            "COMM-W-001 (호스트 통신 재시도 Warning) 가능성",
            "원인: 네트워크 미세 지연",
            "SOP-COMM-001 / FAQ-003 안내",
        ],
        "primary_eq_types": ["CVD", "PVD", "DRY", "WET", "SCN", "CTR", "FUR", "RTP", "HCI", "MCI", "POL", "CLN", "MES", "INS"],
    },
    {
        "target_alarm": "COMM-W-002",
        "target_sop": None,
        "title": "Trend Chart에 짧은 공백 구간이 자주 보입니다",
        "symptom_paragraph": (
            "{eq}의 Trend Chart를 보면 1~2초 정도의 짧은 데이터 결손 구간이 한 시간에 두세 번 정도 보입니다. "
            "별도 알람은 뜨지 않고 있고 다른 SVID도 동시에 끊기는 것으로 보아 DAQ 모듈 jitter 같은데, "
            "이게 정상 범주인지, 조치가 필요한 수준인지 판단해 주세요. "
            "FAQ-002와 FAQ-003 둘 중 어느 쪽에 가까운 사례인지도 알려주시면 좋겠습니다."
        ),
        "key_points": [
            "COMM-W-002 (센서 통신 일시 단절 < 3초) 가능성 — FAQ로 위임",
            "원인: DAQ 모듈 jitter",
            "FAQ-002 / FAQ-003 안내",
        ],
        "primary_eq_types": ["CVD", "PVD", "DRY", "FUR", "RTP", "HCI", "MCI"],
    },
    {
        "target_alarm": "FLOW-M-001",
        "target_sop": "SOP-FLOW-001",
        "title": "MFC setpoint 변경 후 도달 시간이 평소보다 깁니다",
        "symptom_paragraph": (
            "{eq}의 H2 MFC가 setpoint 변경 명령 후 ±5% 도달까지 4~5초가 걸리는 것 같습니다. "
            "spec은 3초 이내라 spec 이탈 가능성이 있고, "
            "Trend로 보면 setpoint 신호와 실측 flow 사이의 lag가 일정하지 않습니다. "
            "MFC controller 노후일 수도 있고, 통신 지연 영향일 수도 있어 진단 순서를 안내해 주세요."
        ),
        "key_points": [
            "FLOW-M-001 (MFC 응답 이상) 가능성",
            "원인: MFC controller 노후 / 통신 지연",
            "SOP-FLOW-001 절차 안내",
        ],
        "primary_eq_types": ["CVD", "DRY"],
    },
    {
        "target_alarm": "CHEM-W-001",
        "target_sop": "SOP-CHEM-001",
        "title": "케미컬 탱크 잔량이 평소보다 빨리 줄어듭니다",
        "symptom_paragraph": (
            "{eq}의 HF 케미컬 탱크 잔량이 평소보다 빠르게 줄고 있어 이번 주에만 두 번이나 20% 미만 경고가 떴습니다. "
            "사용량이 갑자기 늘었다는 공정팀 보고는 없는데 같은 recipe에서 소모량이 늘어난 것 같아 신경 쓰입니다. "
            "정상 범주의 사용량 증가인지, 라인 leak 가능성도 함께 검토해야 하는지 안내 부탁드립니다."
        ),
        "key_points": [
            "CHEM-W-001 (케미컬 보충 필요) 가능성",
            "원인: 사용량 증가",
            "SOP-CHEM-001 / FAQ-004 안내",
        ],
        "primary_eq_types": ["WET", "POL", "CLN", "CTR"],
    },
    {
        "target_alarm": "HV-W-001",
        "target_sop": None,
        "title": "Implanter HV ramp time이 평소보다 길어 보입니다",
        "symptom_paragraph": (
            "{eq}의 0 → setpoint HV ramp time이 baseline 대비 20% 정도 길어 보입니다. "
            "별도 alarm은 뜨지 않고 있고 trip도 발생하지 않았지만, "
            "HV power supply 노후 초기 증상일 수 있을 것 같아 모니터링을 강화해야 할지 판단을 부탁드립니다. "
            "단독 조치가 가능한 항목인지, 정기 PM 시 함께 점검할 사안인지도 알려주세요."
        ),
        "key_points": [
            "HV-W-001 (고전압 RAMP 지연) 가능성 — KB orphan",
            "원인: HV PS 노후",
            "POL-SCOPE-001에 따라 KB 단독 조치 절차 없음 — Trend 모니터링 권장",
        ],
        "primary_eq_types": ["HCI", "MCI", "PVD"],
    },
    {
        "target_alarm": "DOSE-W-001",
        "target_sop": None,
        "title": "post-implant 측정 완료까지 시간이 평소보다 늘었습니다",
        "symptom_paragraph": (
            "{eq}에서 implant 종료 후 post 측정 완료까지의 시간이 baseline 대비 5초 정도 일관되게 늘어났습니다. "
            "라인 throughput에 즉시 영향이 가는 수준은 아니지만, "
            "이 추세가 계속되면 일별 lot 처리량이 줄어드는 것이 우려됩니다. "
            "단순한 measurement queue 적체인지, 단독 조치 가능한 항목인지 판단해 주세요."
        ),
        "key_points": [
            "DOSE-W-001 (Dose 측정 지연) 가능성 — KB orphan",
            "원인: measurement queue 적체",
            "POL-SCOPE-001에 따라 KB 단독 조치 절차 없음 — Trend 모니터링 권장",
        ],
        "primary_eq_types": ["HCI", "MCI"],
    },
    {
        "target_alarm": "PRES-M-001",
        "target_sop": "SOP-PRES-001",
        "title": "공정 압력이 평소보다 미세하게 출렁입니다",
        "symptom_paragraph": (
            "{eq}에서 공정 중 압력이 setpoint 근방에서 ±3~5% 정도 미세하게 출렁이는 패턴이 보입니다. "
            "30초 이동 표준편차가 setpoint × 5% 부근에서 왔다갔다 하고 있어 PRES-M-001 알람이 곧 뜰 것 같은 양상입니다. "
            "throttle valve 미세 진동인지, 가스 라인 진동인지 구분하려면 어떤 데이터를 확인해야 하는지 안내해 주세요."
        ),
        "key_points": [
            "PRES-M-001 (압력 변동 이상, 30초 이동표준편차 > setpoint × 5%) 가능성",
            "원인: 가스 라인 진동 / throttle 미세진동",
            "SOP-PRES-001 절차 안내",
        ],
        "primary_eq_types": ["CVD", "PVD", "DRY"],
    },
    {
        "target_alarm": "COMM-M-001",
        "target_sop": "SOP-COMM-001",
        "title": "MES 응답이 평소보다 느려졌습니다 (S6F11 5초 이상)",
        "symptom_paragraph": (
            "{eq} ↔ MES 사이의 S6F11 응답이 평소 1~2초였는데 오늘은 5~7초까지 늘어났습니다. "
            "MES 측에서 다른 라인 동시 가동이 많아 host load가 높다는 이야기가 있는데, "
            "buffer overflow가 보고된 것은 아닙니다. "
            "이 상태에서 lot 진행을 계속해도 되는지, 임시 대응 절차가 있는지 SOP-COMM-001과 FAQ-007 기준으로 안내해 주세요."
        ),
        "key_points": [
            "COMM-M-001 (SECS/GEM 응답 지연, S6F11 > 5초) 가능성",
            "원인: host load 증가 / buffer overflow",
            "SOP-COMM-001 / FAQ-007 안내",
        ],
        "primary_eq_types": ["CVD", "PVD", "DRY", "WET", "SCN", "CTR", "FUR", "RTP", "HCI", "MCI", "POL", "CLN", "MES", "INS"],
    },
]


def generate_hard_extension_vocs(sot, equipment_rows, user_rows, alarm_code_rows, start_seq):
    """Hard 확장 VOC 15건 — is_core=True, difficulty='hard'."""
    seed = sot["meta"]["generation_seed"] + 3
    rng = random.Random(seed)

    start_date = datetime(2026, 4, 15)
    end_date = datetime(2026, 5, 15)
    duration = (end_date - start_date).days

    code_lookup = {ac["alarm_code"]: ac for ac in alarm_code_rows}
    eq_eng_candidates = [u for u in user_rows if u["role"] in ("EQ_ENG", "PROC_ENG")]

    rows = []
    seq = start_seq
    for spec in HARD_EXTENSION_SPECS:
        ac = code_lookup[spec["target_alarm"]]
        eq_candidates = [
            e for e in equipment_rows
            if e["type"] in spec["primary_eq_types"]
        ]
        eq = rng.choice(eq_candidates) if eq_candidates else rng.choice(equipment_rows)
        user = rng.choice(eq_eng_candidates)
        voc_id = f"VOC-2026-{seq:04d}"
        ts = start_date + timedelta(seconds=rng.randint(0, duration * 86400))
        priority = rng.choices(
            ["NORMAL", "HIGH"],
            weights=[0.6, 0.4],
        )[0]

        opener = _persona_opener(user, eq, rng)
        symptom = spec["symptom_paragraph"].format(eq=eq["equipment_id"])
        ask = rng.choice(CLOSING_PHRASES[priority])
        content = _join_clauses([opener, symptom, ask])

        hints = [f"alarm_code_guide.md#sec-{ac['section_id']}"]
        if spec["target_sop"]:
            hints.append(f"troubleshooting_guide.md#sec-{spec['target_sop']}")

        rows.append({
            "voc_id": voc_id,
            "title": spec["title"],
            "content": content,
            "user_role": user["role"],
            "user_id": user["user_id"],
            "equipment_id": eq["equipment_id"],
            "alarm_code": "",   # Hard VOC: 증상만 기술, 코드 미명시
            "category": "조치 방법 문의",
            "priority": priority,
            "created_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "is_core": True,
            "difficulty": "hard",
            "expected_refusal": False,
            "source_document_hint": hints,
            "expected_key_points": spec["key_points"],
            "expected_answer": "",
        })
        seq += 1
    return rows


def eq_supports_alarm(eq_row, ac_row):
    types = ac_row["applicable_eq_types"].split("|")
    return eq_row["type"] in types


def _filler_source_hint(cat, ac):
    if cat in ("알람 원인 문의", "알람 코드 의미 문의"):
        return [f"alarm_code_guide.md#sec-{ac['section_id']}"]
    if cat == "조치 방법 문의":
        if ac["related_sop_id"]:
            return [
                f"alarm_code_guide.md#sec-{ac['section_id']}",
                f"troubleshooting_guide.md#sec-{ac['related_sop_id']}",
            ]
        return [f"alarm_code_guide.md#sec-{ac['section_id']}"]
    if cat == "Trend Chart 조회 오류":
        return ["system_user_manual.md#sec-SM-TRD-002", "faq.md#sec-FAQ-002"]
    if cat == "데이터 누락 문의":
        return ["system_user_manual.md#sec-SM-TRD-002"]
    if cat == "임계치 설정 문의":
        return ["operation_policy.md#sec-POL-CHG-001", "operation_policy.md#sec-POL-PERM-002"]
    if cat == "설비 상태 불일치":
        return ["faq.md#sec-FAQ-003"]
    if cat == "권한 문제":
        return ["operation_policy.md#sec-POL-PERM-001"]
    if cat == "시스템 접속 오류":
        return ["system_user_manual.md#sec-SM-LOGIN-001", "faq.md#sec-FAQ-001"]
    if cat == "VOC 처리 상태 문의":
        return ["system_user_manual.md#sec-SM-VOC-002", "operation_policy.md#sec-POL-SLA-001"]
    return []


def main():
    sot = load_sot()
    equipment_rows = load_csv(DB_DIR / "equipment_master.csv")
    user_rows = load_csv(DB_DIR / "user_master.csv")
    alarm_code_rows = load_csv(DB_DIR / "alarm_code_master.csv")

    core = list(CORE_VOCS)
    hard_extra = generate_hard_extension_vocs(
        sot, equipment_rows, user_rows, alarm_code_rows,
        start_seq=len(core) + 1,
    )
    fillers = generate_filler_vocs(
        sot, equipment_rows, user_rows, alarm_code_rows,
        start_seq=len(core) + len(hard_extra) + 1,
    )
    all_vocs = core + hard_extra + fillers

    # JSON
    VOC_DIR.mkdir(parents=True, exist_ok=True)
    with open(VOC_DIR / "voc_samples.json", "w", encoding="utf-8") as f:
        json.dump({"vocs": all_vocs, "meta": {
            "total": len(all_vocs),
            "core_count": sum(1 for v in all_vocs if v.get("is_core")),
            "filler_count": sum(1 for v in all_vocs if not v.get("is_core")),
            "hard_extra_count": len(hard_extra),
        }}, f, ensure_ascii=False, indent=2)
    print(f"  [OK] voc_samples.json  ({len(all_vocs)} entries, "
          f"core={len(core) + len(hard_extra)} [orig 30 + hard 15], "
          f"filler={len(fillers)})")

    # CSV (평탄화: 리스트 필드는 |로 join)
    fieldnames = [
        "voc_id", "title", "content", "user_role", "user_id",
        "equipment_id", "alarm_code", "category", "priority", "created_at",
        "is_core", "difficulty", "expected_refusal",
        "source_document_hint", "expected_key_points",
    ]
    with open(VOC_DIR / "voc_samples.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for v in all_vocs:
            row = {k: v.get(k, "") for k in fieldnames}
            row["source_document_hint"] = "|".join(v.get("source_document_hint", []) or [])
            row["expected_key_points"] = "|".join(v.get("expected_key_points", []) or [])
            row["is_core"] = "Y" if v.get("is_core") else "N"
            row["expected_refusal"] = "Y" if v.get("expected_refusal") else "N"
            writer.writerow(row)
    print(f"  [OK] voc_samples.csv  ({len(all_vocs)} rows)")


if __name__ == "__main__":
    main()
