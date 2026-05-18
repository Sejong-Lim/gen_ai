#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
validate_integrity.py — 전체 데이터 레이어 무결성 검증.

검증 항목:
  [A] Source-of-truth 내부 무결성
      A1. alarm_codes.related_sop_id 가 sops.id 에 존재 (null 허용)
      A2. alarm_codes.section_id 가 AC-<code> 패턴 일치
      A3. alarm_codes.applicable_eq_types 가 equipment_types.id 에 존재
      A4. sops.related_alarm_codes 가 alarm_codes.code 에 존재
      A5. equipment.type 이 equipment_types.id 에 존재
      A6. severity / category 코드 일관성

  [B] 매뉴얼 anchor 추출 및 SOT 일치
      B1. 매뉴얼별 헤더에서 추출한 section_id 가 SOT 정의와 일치
      B2. SOT 의 모든 section_id 가 매뉴얼에 실제 존재
      B3. 매뉴얼에 정의되었으나 SOT 에 없는 anchor 가 없음
      B4. 매뉴얼 본문의 [code]·[section_id] 상호 참조가 실재

  [C] DB CSV ↔ SOT 일치
      C1. equipment_master 의 모든 equipment_id ∈ SOT.equipment
      C2. alarm_code_master 의 모든 alarm_code ∈ SOT.alarm_codes
      C3. user_master 의 모든 user_id ∈ SOT.users
      C4. alarm_history.equipment_id / alarm_code 가 master 에 존재
      C5. alarm_history.alarm_code 가 해당 equipment.type 에 적용 가능
      C6. voc_history.equipment_id / alarm_code / user_id 가 master 에 존재

  [D] VOC ↔ 매뉴얼 citation 무결성
      D1. voc_samples 의 source_document_hint 가 매뉴얼 실존 anchor 일치
      D2. voc_samples 의 equipment_id / alarm_code 가 master 에 존재
         (단, difficulty=trap 인 경우는 의도적 미존재 — 검증 대상에서 제외)
      D3. voc_samples 의 user_id 가 master 에 존재
      D4. 핵심 VOC ≥ 30건이고 모두 정의된 difficulty 라벨 (easy/medium/hard/edge/trap/multi_turn)

  [E] 평가셋 ↔ 매뉴얼 citation 무결성
      E1. test_questions.gold_docs 가 매뉴얼 실존 anchor
      E2. expected_refusal=True 인 항목은 expected_intent='out_of_scope'
          또는 difficulty in (edge, trap)

  [F] 분포 검증
      F1. 핵심 30건의 difficulty 분포: easy/medium/hard/edge/trap/multi_turn 모두 포함
      F2. VOC 전체 카테고리 분포가 0 이 아님

  [G] 신규 확장 필드 무결성 (citation_display_name / root_cause_tags /
      symptom_keywords / recommended_questions)
      G1. citation_display_name 길이 ≤ 60 (WARN)
      G2. root_cause_tags 의 모든 값이 taxonomies/root_cause_tags.yaml 에 존재 (FAIL)
      G3. recommended_questions[].target_section_id 가 SOT 내 존재 (FAIL)
      G4. recommended_questions[].target_intent 가 taxonomies/intents.yaml 에 존재 (FAIL)
      G5. recommended_questions 각 엔트리는 target_section_id XOR target_intent (FAIL)
      G6. alarm_codes 의 symptom_keywords 3 개 이상 (WARN, has_documented_action=true 한정)
      G7. has_documented_action=false 인 alarm 은 root_cause_tags 면제

종료 코드:
  0 — 통과 (warning 있어도 통과)
  1 — 오류 (failure 존재)
"""

import csv
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Windows 콘솔에서 한글/특수문자 출력을 위해 stdout 을 UTF-8 로 재설정
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import yaml
except ImportError:
    sys.exit("pyyaml이 필요합니다.")

ROOT = Path(__file__).resolve().parent.parent
SOT_PATH = ROOT / "data" / "_meta" / "source_of_truth.yaml"
TAX_DIR = ROOT / "data" / "_meta" / "taxonomies"
TAX_ROOT_CAUSE = TAX_DIR / "root_cause_tags.yaml"
TAX_INTENTS = TAX_DIR / "intents.yaml"
DB_DIR = ROOT / "data" / "db"
VOC_PATH = ROOT / "data" / "voc" / "voc_samples.json"
EVAL_DIR = ROOT / "data" / "evaluation"
MANUAL_DIR = ROOT / "data" / "manuals"

MANUAL_FILES = {
    "alarm_code_guide.md": MANUAL_DIR / "alarm_code_guide.md",
    "troubleshooting_guide.md": MANUAL_DIR / "troubleshooting_guide.md",
    "operation_policy.md": MANUAL_DIR / "operation_policy.md",
    "system_user_manual.md": MANUAL_DIR / "system_user_manual.md",
    "faq.md": MANUAL_DIR / "faq.md",
}

# section_id 추출 패턴: "## <ID> | <title>"  또는 "### <ID> | ..."
SECTION_HEADER_RE = re.compile(r"^#{2,3}\s+([A-Z]+-[A-Z0-9-]+)\s*\|", re.MULTILINE)


class Report:
    def __init__(self):
        self.failures = []
        self.warnings = []
        self.checks_passed = 0

    def fail(self, code, msg):
        self.failures.append((code, msg))

    def warn(self, code, msg):
        self.warnings.append((code, msg))

    def passed(self, code):
        self.checks_passed += 1

    def summary(self):
        print()
        print("=" * 70)
        print(f"검사 통과: {self.checks_passed}")
        print(f"경고:       {len(self.warnings)}")
        print(f"오류:       {len(self.failures)}")
        print("=" * 70)
        if self.warnings:
            print("\n[WARNINGS]")
            for c, m in self.warnings:
                print(f"  - [{c}] {m}")
        if self.failures:
            print("\n[FAILURES]")
            for c, m in self.failures:
                print(f"  - [{c}] {m}")
            return 1
        print("\n[OK] 모든 무결성 검증 통과.")
        return 0


def load_yaml():
    with open(SOT_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def extract_anchors_from_manual(path):
    """매뉴얼 파일에서 section_id 목록 추출 (출현 순서 보존)."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return SECTION_HEADER_RE.findall(text)


def extract_referenced_ids_from_text(text):
    """매뉴얼 본문에서 참조된 [XXX-YYY] 또는 §XXX-YYY 패턴 추출."""
    refs = set()
    for m in re.finditer(r"\[([A-Z]+-[A-Z0-9-]+)\]", text):
        refs.add(m.group(1))
    for m in re.finditer(r"§([A-Z]+-[A-Z0-9-]+)", text):
        refs.add(m.group(1))
    return refs


# =============================================================================
# Check A — SOT 내부 무결성
# =============================================================================
def check_sot_internal(sot, rep):
    print("\n[A] Source-of-truth 내부 무결성")
    sop_ids = {s["id"] for s in sot["sops"]}
    alarm_codes = {ac["code"]: ac for ac in sot["alarm_codes"]}
    eq_type_ids = {t["id"] for t in sot["equipment_types"]}
    sev_ids = {s["id"] for s in sot["severities"]}
    cat_ids = {c["id"] for c in sot["alarm_categories"]}

    # A1
    for ac in sot["alarm_codes"]:
        if ac["related_sop_id"] is not None and ac["related_sop_id"] not in sop_ids:
            rep.fail("A1", f"alarm {ac['code']}.related_sop_id={ac['related_sop_id']} not in sops")
    rep.passed("A1")

    # A2 section_id 패턴 일치 (AC-<code>)
    for ac in sot["alarm_codes"]:
        expected = f"AC-{ac['code']}"
        if ac["section_id"] != expected:
            rep.fail("A2", f"alarm {ac['code']}.section_id={ac['section_id']} != {expected}")
    rep.passed("A2")

    # A3 applicable_eq_types
    for ac in sot["alarm_codes"]:
        for t in ac["applicable_eq_types"]:
            if t not in eq_type_ids:
                rep.fail("A3", f"alarm {ac['code']}.applicable_eq_types includes unknown type {t}")
    rep.passed("A3")

    # A4 sops.related_alarm_codes ⊂ alarm_codes
    for s in sot["sops"]:
        for c in s["related_alarm_codes"]:
            if c not in alarm_codes:
                rep.fail("A4", f"sop {s['id']}.related_alarm_codes includes unknown {c}")
    rep.passed("A4")

    # A5 equipment.type ⊂ equipment_types
    for eq in sot["equipment"]:
        if eq["type"] not in eq_type_ids:
            rep.fail("A5", f"equipment {eq['id']}.type={eq['type']} not in equipment_types")
    rep.passed("A5")

    # A6 severity / category 일관성
    for ac in sot["alarm_codes"]:
        if ac["severity"] not in sev_ids:
            rep.fail("A6", f"alarm {ac['code']}.severity={ac['severity']} not in severities")
        if ac["category"] not in cat_ids:
            rep.fail("A6", f"alarm {ac['code']}.category={ac['category']} not in alarm_categories")
        # section_id 의 Severity 토큰이 일치
        # AC-CATEGORY-SEV-NNN → code = CATEGORY-SEV-NNN
        if ac["section_id"][3:] != ac["code"]:
            rep.fail("A6", f"alarm {ac['code']}.section_id 와 code 불일치")
    rep.passed("A6")


# =============================================================================
# Check B — 매뉴얼 anchor 일치
# =============================================================================
def check_manual_anchors(sot, rep):
    print("\n[B] 매뉴얼 anchor 추출 및 SOT 일치")

    # 1) 매뉴얼별 anchor 추출
    manual_anchors = {fname: extract_anchors_from_manual(path)
                      for fname, path in MANUAL_FILES.items()}
    flat = {}
    for fname, anchors in manual_anchors.items():
        for a in anchors:
            if a in flat:
                rep.fail("B0", f"중복 anchor: {a} ({flat[a]} 와 {fname})")
            flat[a] = fname

    # 2) SOT 가 정의한 anchor 들
    sot_anchors = {}
    for ac in sot["alarm_codes"]:
        sot_anchors[ac["section_id"]] = "alarm_code_guide.md"
    for s in sot["sops"]:
        sot_anchors[s["section_id"]] = "troubleshooting_guide.md"
    for p in sot["policies"]:
        sot_anchors[p["section_id"]] = "operation_policy.md"
    for m in sot["manual_sections"]:
        sot_anchors[m["section_id"]] = "system_user_manual.md"
    for f in sot["faq_sections"]:
        sot_anchors[f["section_id"]] = "faq.md"

    # B1 / B2 — SOT 에 정의된 anchor 가 모두 매뉴얼에 존재
    for anchor, expected_file in sot_anchors.items():
        if anchor not in flat:
            rep.fail("B1", f"SOT 정의 anchor {anchor} 가 어느 매뉴얼에도 없음")
            continue
        if flat[anchor] != expected_file:
            rep.fail("B1", f"anchor {anchor} 는 {expected_file} 에 있어야 하나 {flat[anchor]} 에 있음")
    rep.passed("B1")

    # B3 — 매뉴얼에 있으나 SOT 에 없는 anchor (예외 허용: 매뉴얼 자체의 임시 anchor 없음)
    for anchor in flat:
        if anchor not in sot_anchors:
            rep.warn("B3", f"매뉴얼 anchor {anchor} 가 SOT 에 정의되지 않음 ({flat[anchor]})")
    rep.passed("B3")

    # B4 — 매뉴얼 본문의 참조가 실재 anchor
    for fname, path in MANUAL_FILES.items():
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        for ref in extract_referenced_ids_from_text(text):
            # 알람 코드(TEMP-H-001) vs section_id(AC-TEMP-H-001) 둘 다 허용
            if ref in sot_anchors:
                continue
            # 알람 코드 직접 참조 허용
            if any(ac["code"] == ref for ac in sot["alarm_codes"]):
                continue
            # SOP/POL/SM/FAQ id 직접 참조 허용
            if any(s["id"] == ref for s in sot["sops"]):
                continue
            rep.fail("B4", f"{fname} 본문 참조 [{ref}] 가 실재 anchor/code 아님")
    rep.passed("B4")


# =============================================================================
# Check C — DB CSV 일치
# =============================================================================
def check_db_csvs(sot, rep):
    print("\n[C] DB CSV ↔ SOT 일치")
    sot_eq = {e["id"] for e in sot["equipment"]}
    sot_ac = {ac["code"] for ac in sot["alarm_codes"]}
    sot_user = {u["id"] for u in sot["users"]}

    # 마스터 CSV 로드
    eq_rows = load_csv(DB_DIR / "equipment_master.csv")
    ac_rows = load_csv(DB_DIR / "alarm_code_master.csv")
    user_rows = load_csv(DB_DIR / "user_master.csv")
    hist_rows = load_csv(DB_DIR / "alarm_history.csv")
    voc_hist_rows = load_csv(DB_DIR / "voc_history.csv")

    # C1
    csv_eq_ids = {r["equipment_id"] for r in eq_rows}
    if csv_eq_ids != sot_eq:
        rep.fail("C1", f"equipment_master 와 SOT.equipment 불일치 (diff={csv_eq_ids ^ sot_eq})")
    rep.passed("C1")

    # C2
    csv_ac_codes = {r["alarm_code"] for r in ac_rows}
    if csv_ac_codes != sot_ac:
        rep.fail("C2", f"alarm_code_master 와 SOT.alarm_codes 불일치 (diff={csv_ac_codes ^ sot_ac})")
    rep.passed("C2")

    # C3
    csv_user_ids = {r["user_id"] for r in user_rows}
    if csv_user_ids != sot_user:
        rep.fail("C3", f"user_master 와 SOT.users 불일치 (diff={csv_user_ids ^ sot_user})")
    rep.passed("C3")

    # C4
    for r in hist_rows:
        if r["equipment_id"] not in csv_eq_ids:
            rep.fail("C4", f"alarm_history {r['alarm_event_id']}.equipment_id={r['equipment_id']} not in equipment_master")
            break
        if r["alarm_code"] not in csv_ac_codes:
            rep.fail("C4", f"alarm_history {r['alarm_event_id']}.alarm_code={r['alarm_code']} not in alarm_code_master")
            break
    rep.passed("C4")

    # C5 — applicable_eq_types 일치
    eq_type_lookup = {r["equipment_id"]: r["type"] for r in eq_rows}
    ac_applicable_lookup = {r["alarm_code"]: r["applicable_eq_types"].split("|") for r in ac_rows}
    violations = 0
    for r in hist_rows:
        eq_type = eq_type_lookup[r["equipment_id"]]
        applicable = ac_applicable_lookup[r["alarm_code"]]
        if eq_type not in applicable:
            violations += 1
            if violations <= 3:
                rep.fail("C5", f"alarm_history {r['alarm_event_id']}: code {r['alarm_code']} not applicable to type {eq_type} (eq={r['equipment_id']})")
    if violations > 3:
        rep.fail("C5", f"...총 {violations}건의 위반")
    if violations == 0:
        rep.passed("C5")

    # C6 — voc_history
    for r in voc_hist_rows:
        if r["equipment_id"] and r["equipment_id"] not in csv_eq_ids:
            rep.fail("C6", f"voc_history {r['voc_id']}.equipment_id={r['equipment_id']} not in master")
            break
        if r["alarm_code"] and r["alarm_code"] not in csv_ac_codes:
            rep.fail("C6", f"voc_history {r['voc_id']}.alarm_code={r['alarm_code']} not in master")
            break
        if r["user_id"] and r["user_id"] not in csv_user_ids:
            rep.fail("C6", f"voc_history {r['voc_id']}.user_id={r['user_id']} not in master")
            break
    rep.passed("C6")


# =============================================================================
# Check D — VOC ↔ 매뉴얼 citation 무결성
# =============================================================================
def check_voc_citations(sot, rep):
    print("\n[D] VOC ↔ 매뉴얼 citation 무결성")

    with open(VOC_PATH, "r", encoding="utf-8") as f:
        voc_data = json.load(f)

    # 매뉴얼 anchor 인덱스
    file_anchors = {fname: set(extract_anchors_from_manual(path))
                    for fname, path in MANUAL_FILES.items()}

    eq_ids = {e["id"] for e in sot["equipment"]}
    ac_codes = {ac["code"] for ac in sot["alarm_codes"]}
    user_ids = {u["id"] for u in sot["users"]}

    # D1 source_document_hint 검증
    d1_failed = 0
    for v in voc_data["vocs"]:
        for hint in v.get("source_document_hint", []) or []:
            if "#" not in hint:
                rep.fail("D1", f"VOC {v['voc_id']} hint '{hint}' missing '#'")
                d1_failed += 1
                continue
            fname, anchor = hint.split("#", 1)
            anchor = anchor.replace("sec-", "")
            if fname not in file_anchors:
                rep.fail("D1", f"VOC {v['voc_id']} hint references unknown file '{fname}'")
                d1_failed += 1
                continue
            if anchor not in file_anchors[fname]:
                rep.fail("D1", f"VOC {v['voc_id']} hint anchor '{anchor}' not in {fname}")
                d1_failed += 1
    if d1_failed == 0:
        rep.passed("D1")

    # D2 entity 검증 — trap 은 의도적 invalid 이므로 제외
    for v in voc_data["vocs"]:
        if v.get("difficulty") == "trap":
            continue
        if v.get("equipment_id") and v["equipment_id"] not in eq_ids:
            rep.fail("D2", f"VOC {v['voc_id']}.equipment_id={v['equipment_id']} not in master (non-trap)")
        if v.get("alarm_code") and v["alarm_code"] not in ac_codes:
            rep.fail("D2", f"VOC {v['voc_id']}.alarm_code={v['alarm_code']} not in master (non-trap)")
    rep.passed("D2")

    # D3 user_id
    for v in voc_data["vocs"]:
        if v.get("user_id") and v["user_id"] not in user_ids:
            rep.fail("D3", f"VOC {v['voc_id']}.user_id={v['user_id']} not in master")
    rep.passed("D3")

    # D4 핵심 VOC 의 difficulty 라벨
    #   - 최소 30건 (기존 손정의 30건)
    #   - difficulty 는 정의된 6 종 라벨 중 하나
    core_count = sum(1 for v in voc_data["vocs"] if v.get("is_core"))
    if core_count < 30:
        rep.fail("D4", f"핵심 VOC 수 = {core_count}, 최소 30 기대")
    valid_diff = {"easy", "medium", "hard", "edge", "trap", "multi_turn"}
    for v in voc_data["vocs"]:
        if v.get("is_core") and v.get("difficulty") not in valid_diff:
            rep.fail("D4", f"핵심 VOC {v['voc_id']} difficulty={v.get('difficulty')} invalid")
    rep.passed("D4")


# =============================================================================
# Check E — 평가셋 무결성
# =============================================================================
def check_eval_set(sot, rep):
    print("\n[E] 평가셋 ↔ 매뉴얼 citation 무결성")

    file_anchors = {fname: set(extract_anchors_from_manual(path))
                    for fname, path in MANUAL_FILES.items()}

    with open(EVAL_DIR / "test_questions.json", "r", encoding="utf-8") as f:
        ts = json.load(f)["tests"]

    e1_failed = 0
    for t in ts:
        for hint in t.get("gold_docs", []) or []:
            if "#" not in hint:
                rep.fail("E1", f"{t['qid']} gold_doc '{hint}' missing '#'")
                e1_failed += 1
                continue
            fname, anchor = hint.split("#", 1)
            anchor = anchor.replace("sec-", "")
            if fname not in file_anchors:
                rep.fail("E1", f"{t['qid']} unknown file '{fname}'")
                e1_failed += 1
                continue
            if anchor not in file_anchors[fname]:
                rep.fail("E1", f"{t['qid']} anchor '{anchor}' not in {fname}")
                e1_failed += 1
    if e1_failed == 0:
        rep.passed("E1")

    # E2
    for t in ts:
        if t.get("expected_refusal"):
            ok = (t.get("expected_intent") == "out_of_scope"
                  or t.get("difficulty") in ("edge", "trap"))
            if not ok:
                rep.fail("E2", f"{t['qid']} expected_refusal=True 인데 intent/difficulty 부적합 "
                               f"(intent={t.get('expected_intent')}, diff={t.get('difficulty')})")
    rep.passed("E2")


# =============================================================================
# Check F — 분포 검증
# =============================================================================
def check_distribution(sot, rep):
    print("\n[F] 분포 검증")
    with open(VOC_PATH, "r", encoding="utf-8") as f:
        voc_data = json.load(f)

    # F1 — 핵심 VOC 에 6 difficulty 모두 포함
    core = [v for v in voc_data["vocs"] if v.get("is_core")]
    diffs = {v["difficulty"] for v in core}
    required = {"easy", "medium", "hard", "edge", "trap", "multi_turn"}
    missing = required - diffs
    if missing:
        rep.fail("F1", f"핵심 VOC 에서 누락된 difficulty: {missing}")
    rep.passed("F1")

    # F2 — VOC 전체 카테고리 분포
    cat_counts = defaultdict(int)
    for v in voc_data["vocs"]:
        cat_counts[v["category"]] += 1
    if len(cat_counts) < 5:
        rep.fail("F2", f"카테고리 종류가 너무 적음 ({len(cat_counts)})")
    print("    카테고리 분포:")
    for c, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"      {c}: {n}")
    print(f"    핵심 30건 difficulty 분포: " +
          ", ".join(f"{d}={sum(1 for v in core if v['difficulty']==d)}" for d in sorted(required)))
    rep.passed("F2")


# =============================================================================
# Check G — 신규 확장 필드 무결성
# =============================================================================
CITATION_DISPLAY_MAX = 60
ALARM_SYMPTOM_MIN = 3


def _load_taxonomies():
    with open(TAX_ROOT_CAUSE, "r", encoding="utf-8") as f:
        rc = yaml.safe_load(f)
    with open(TAX_INTENTS, "r", encoding="utf-8") as f:
        it = yaml.safe_load(f)
    return (
        {t["id"] for t in rc.get("tags", [])},
        {i["id"] for i in it.get("intents", [])},
    )


def _all_section_ids(sot):
    s = set()
    for ac in sot["alarm_codes"]:
        s.add(ac["section_id"])
    for sp in sot["sops"]:
        s.add(sp["section_id"])
    for p in sot["policies"]:
        s.add(p["section_id"])
    for m in sot["manual_sections"]:
        s.add(m["section_id"])
    for fq in sot["faq_sections"]:
        s.add(fq["section_id"])
    return s


def _entry_label(e, kind):
    return e.get("code") or e.get("id") or e.get("section_id") or f"<{kind}>"


def check_extension_fields(sot, rep):
    print("\n[G] 신규 확장 필드 무결성")

    try:
        valid_tags, valid_intents = _load_taxonomies()
    except FileNotFoundError as ex:
        rep.fail("G0", f"taxonomy 파일을 찾을 수 없음: {ex}")
        return

    all_sections = _all_section_ids(sot)

    groups = [
        ("alarm", sot["alarm_codes"]),
        ("sop", sot["sops"]),
        ("policy", sot["policies"]),
        ("faq", sot["faq_sections"]),
        ("manual", sot["manual_sections"]),
    ]

    # G1 — citation_display_name 길이
    for kind, entries in groups:
        for e in entries:
            cdn = e.get("citation_display_name")
            if cdn and len(cdn) > CITATION_DISPLAY_MAX:
                rep.warn(
                    "G1",
                    f"{kind} {_entry_label(e, kind)} citation_display_name 길이 "
                    f"{len(cdn)} > {CITATION_DISPLAY_MAX}",
                )
    rep.passed("G1")

    # G2 — root_cause_tags 마스터 검증 (alarm/sop)
    for kind in ("alarm", "sop"):
        entries = sot["alarm_codes"] if kind == "alarm" else sot["sops"]
        for e in entries:
            # G7: has_documented_action=false 인 alarm 은 면제
            if kind == "alarm" and not e.get("has_documented_action", True):
                continue
            tags = e.get("root_cause_tags") or []
            for t in tags:
                if t not in valid_tags:
                    rep.fail(
                        "G2",
                        f"{kind} {_entry_label(e, kind)}: root_cause_tag "
                        f"'{t}' not in taxonomy",
                    )
    rep.passed("G2")

    # G3/G4/G5 — recommended_questions 검증
    for kind, entries in groups:
        for e in entries:
            rqs = e.get("recommended_questions") or []
            for i, rq in enumerate(rqs):
                tsi = rq.get("target_section_id")
                tin = rq.get("target_intent")
                label = f"{kind} {_entry_label(e, kind)}.rq[{i}]"
                # G5: XOR
                if bool(tsi) == bool(tin):
                    rep.fail(
                        "G5",
                        f"{label}: target_section_id XOR target_intent 위반 "
                        f"(section={tsi!r}, intent={tin!r})",
                    )
                    continue
                # G3
                if tsi and tsi not in all_sections:
                    rep.fail("G3", f"{label}: target_section_id '{tsi}' 미존재")
                # G4
                if tin and tin not in valid_intents:
                    rep.fail("G4", f"{label}: target_intent '{tin}' not in taxonomy")
    rep.passed("G3")
    rep.passed("G4")
    rep.passed("G5")

    # G6 — alarm symptom_keywords 최소 개수 (has_documented_action=true 한정)
    for ac in sot["alarm_codes"]:
        if not ac.get("has_documented_action", True):
            continue
        sym = ac.get("symptom_keywords") or []
        if len(sym) < ALARM_SYMPTOM_MIN:
            rep.warn(
                "G6",
                f"alarm {ac['code']} symptom_keywords {len(sym)} < {ALARM_SYMPTOM_MIN}",
            )
    rep.passed("G6")

    # G7 — has_documented_action=false 면제 (위 G2에서 skip 처리됨)
    rep.passed("G7")


def main():
    rep = Report()

    sot = load_yaml()
    print("=" * 70)
    print("FDC-Monitoring AI System — 데이터 레이어 무결성 검증")
    print("=" * 70)

    check_sot_internal(sot, rep)
    check_manual_anchors(sot, rep)
    check_db_csvs(sot, rep)
    check_voc_citations(sot, rep)
    check_eval_set(sot, rep)
    check_distribution(sot, rep)
    check_extension_fields(sot, rep)

    sys.exit(rep.summary())


if __name__ == "__main__":
    main()
