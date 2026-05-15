#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_db.py — Source-of-truth YAML로부터 data/db/*.csv 파생.

생성 파일:
  data/db/equipment_master.csv
  data/db/alarm_code_master.csv
  data/db/user_master.csv
  data/db/alarm_history.csv      (시드 고정 — 재현 가능)
  data/db/voc_history.csv        (시드 고정)

사용:
  python scripts/build_db.py
"""

import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml이 필요합니다.  pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
SOT_PATH = ROOT / "data" / "_meta" / "source_of_truth.yaml"
DB_DIR = ROOT / "data" / "db"


def load_sot():
    with open(SOT_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_csv(path: Path, fieldnames: list, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"  [OK] {path.relative_to(ROOT)}  ({len(rows)} rows)")


def build_equipment_master(sot):
    rows = []
    for eq in sot["equipment"]:
        rows.append({
            "equipment_id": eq["id"],
            "type": eq["type"],
            "process": next(t["process"] for t in sot["equipment_types"] if t["id"] == eq["type"]),
            "full_name": next(t["full_name"] for t in sot["equipment_types"] if t["id"] == eq["type"]),
            "location": eq["location"],
            "vendor": eq["vendor"],
            "install_year": eq["install_year"],
            "chambers": "|".join(eq["chambers"]) if eq["chambers"] else "",
            "status": eq["status"],
        })
    write_csv(
        DB_DIR / "equipment_master.csv",
        ["equipment_id", "type", "process", "full_name", "location",
         "vendor", "install_year", "chambers", "status"],
        rows,
    )
    return rows


def build_alarm_code_master(sot):
    rows = []
    for ac in sot["alarm_codes"]:
        rows.append({
            "alarm_code": ac["code"],
            "name": ac["name"],
            "category": ac["category"],
            "severity": ac["severity"],
            "threshold_text": ac["threshold_text"],
            "typical_causes": "|".join(ac["typical_causes"]),
            "applicable_eq_types": "|".join(ac["applicable_eq_types"]),
            "related_sop_id": ac["related_sop_id"] or "",
            "section_id": ac["section_id"],
            "has_documented_action": "Y" if ac["has_documented_action"] else "N",
        })
    write_csv(
        DB_DIR / "alarm_code_master.csv",
        ["alarm_code", "name", "category", "severity", "threshold_text",
         "typical_causes", "applicable_eq_types", "related_sop_id",
         "section_id", "has_documented_action"],
        rows,
    )
    return rows


def build_user_master(sot):
    rows = []
    for u in sot["users"]:
        rows.append({
            "user_id": u["id"],
            "name": u["name"],
            "role": u["role"],
            "team": u["team"],
            "email": u["email"],
        })
    write_csv(
        DB_DIR / "user_master.csv",
        ["user_id", "name", "role", "team", "email"],
        rows,
    )
    return rows


def build_alarm_history(sot, equipment_rows, alarm_code_rows):
    """알람 발생 이력 — 시드 고정으로 재현 가능."""
    cfg = sot["derivation"]["alarm_history"]
    seed = sot["meta"]["generation_seed"]
    rng = random.Random(seed)

    start = datetime.fromisoformat(cfg["date_range"][0])
    end = datetime.fromisoformat(cfg["date_range"][1])
    duration_days = (end - start).days

    # severity 가중치 → 알람 코드 weight
    sev_weights = cfg["severity_distribution"]
    code_to_eq_types = {ac["alarm_code"]: ac["applicable_eq_types"].split("|") for ac in alarm_code_rows}
    code_to_severity = {ac["alarm_code"]: ac["severity"] for ac in alarm_code_rows}

    # 설비 가중치 — hotspot 설비는 3배 자주 발생
    hotspot = set(cfg["hotspot_equipment"])
    eq_weights = []
    for eq in equipment_rows:
        weight = 3 if eq["equipment_id"] in hotspot else 1
        if eq["status"] == "MAINTENANCE":
            weight = 0.3
        eq_weights.append((eq, weight))

    rows = []
    target = cfg["target_rows"]
    n = 0
    attempts = 0
    while n < target and attempts < target * 5:
        attempts += 1
        # 1) 설비 추출
        eq = rng.choices([e for e, _ in eq_weights], weights=[w for _, w in eq_weights])[0]
        # 2) 해당 설비 type에 가능한 알람코드 풀
        candidate_codes = [c for c, types in code_to_eq_types.items() if eq["type"] in types]
        if not candidate_codes:
            continue
        # 3) severity 분포에 따라 가중 추출
        code_weights = [sev_weights.get(code_to_severity[c], 0.1) for c in candidate_codes]
        code = rng.choices(candidate_codes, weights=code_weights)[0]
        sev = code_to_severity[code]
        # 4) 타임스탬프
        ts = start + timedelta(
            seconds=rng.randint(0, duration_days * 24 * 3600)
        )
        # 5) 챔버
        chambers = eq["chambers"].split("|") if eq["chambers"] else []
        chamber = rng.choice(chambers) if chambers else ""
        # 6) duration / status
        dur = {"C": rng.randint(60, 1800), "H": rng.randint(30, 900),
               "M": rng.randint(10, 300), "W": rng.randint(5, 120),
               "I": rng.randint(1, 30)}[sev]
        status = rng.choices(
            ["CLEARED", "ACKNOWLEDGED", "OPEN"],
            weights=[0.85, 0.12, 0.03],
        )[0]
        # 7) recipe / lot (선택적)
        recipe = f"R-{eq['type']}-{rng.randint(1,30):02d}" if rng.random() < 0.7 else ""
        lot = f"LOT-{ts.strftime('%Y%m%d')}-{rng.randint(1,200):03d}" if rng.random() < 0.6 else ""

        rows.append({
            "alarm_event_id": f"AE-{ts.strftime('%Y%m%d')}-{n+1:04d}",
            "occurred_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "equipment_id": eq["equipment_id"],
            "chamber": chamber,
            "alarm_code": code,
            "severity": sev,
            "duration_sec": dur,
            "status": status,
            "recipe_id": recipe,
            "lot_id": lot,
        })
        n += 1

    rows.sort(key=lambda r: r["occurred_at"])
    # 정렬 후 ID 재발번 (시간순)
    for i, r in enumerate(rows):
        ts = datetime.strptime(r["occurred_at"], "%Y-%m-%d %H:%M:%S")
        r["alarm_event_id"] = f"AE-{ts.strftime('%Y%m%d')}-{i+1:04d}"

    write_csv(
        DB_DIR / "alarm_history.csv",
        ["alarm_event_id", "occurred_at", "equipment_id", "chamber", "alarm_code",
         "severity", "duration_sec", "status", "recipe_id", "lot_id"],
        rows,
    )
    return rows


def build_voc_history(sot, equipment_rows, user_rows, alarm_code_rows):
    """과거 VOC 이력 (voc_samples.json 의 100건과는 별개의 처리 이력)."""
    cfg = sot["derivation"]["voc_history"]
    seed = sot["meta"]["generation_seed"] + 1
    rng = random.Random(seed)

    start = datetime.fromisoformat(cfg["date_range"][0])
    end = datetime.fromisoformat(cfg["date_range"][1])
    duration_days = (end - start).days

    categories = [
        "알람 원인 문의", "조치 방법 문의", "Trend Chart 조회 오류",
        "데이터 누락 문의", "임계치 설정 문의", "설비 상태 불일치",
        "권한 문제", "시스템 접속 오류", "알람 코드 의미 문의",
        "VOC 처리 상태 문의",
    ]
    priorities = ["LOW", "NORMAL", "HIGH", "URGENT"]
    pri_weights = [0.20, 0.55, 0.20, 0.05]

    eq_eng_users = [u for u in user_rows if u["role"] in ("EQ_ENG", "PROC_ENG")]
    eq_ids = [e["equipment_id"] for e in equipment_rows]
    code_ids = [ac["alarm_code"] for ac in alarm_code_rows]

    status_dist = cfg["status_distribution"]

    rows = []
    target = cfg["target_rows"]
    for i in range(target):
        ts = start + timedelta(
            seconds=rng.randint(0, duration_days * 24 * 3600)
        )
        user = rng.choice(user_rows)
        cat = rng.choice(categories)
        pri = rng.choices(priorities, weights=pri_weights)[0]

        eq_id = rng.choice(eq_ids) if rng.random() < 0.8 else ""
        alarm_code = rng.choice(code_ids) if cat in ("알람 원인 문의", "조치 방법 문의", "알람 코드 의미 문의") and rng.random() < 0.75 else ""

        status = rng.choices(
            list(status_dist.keys()),
            weights=list(status_dist.values()),
        )[0]

        resolved_at = ""
        assignee_id = ""
        if status in ("RESOLVED", "CLOSED"):
            resolved_at = (ts + timedelta(hours=rng.randint(1, 72))).strftime("%Y-%m-%d %H:%M:%S")
            assignee_id = rng.choice(eq_eng_users)["user_id"]
        elif status == "IN_PROGRESS":
            assignee_id = rng.choice(eq_eng_users)["user_id"]

        rows.append({
            "voc_id": f"VOC-2026-H{i+1:04d}",
            "created_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user["user_id"],
            "title": _gen_voc_title(cat, eq_id, alarm_code, rng),
            "category": cat,
            "priority": pri,
            "equipment_id": eq_id,
            "alarm_code": alarm_code,
            "status": status,
            "assignee_id": assignee_id,
            "resolved_at": resolved_at,
        })

    rows.sort(key=lambda r: r["created_at"])
    write_csv(
        DB_DIR / "voc_history.csv",
        ["voc_id", "created_at", "user_id", "title", "category", "priority",
         "equipment_id", "alarm_code", "status", "assignee_id", "resolved_at"],
        rows,
    )
    return rows


def _gen_voc_title(cat, eq_id, alarm_code, rng):
    if cat == "알람 원인 문의":
        return f"{alarm_code or '알람'} 원인 확인 요청" + (f" ({eq_id})" if eq_id else "")
    if cat == "조치 방법 문의":
        return f"{alarm_code or '알람'} 조치 방법 안내 요청"
    if cat == "Trend Chart 조회 오류":
        return f"Trend Chart 데이터 표시 안됨 ({eq_id})" if eq_id else "Trend Chart 조회 불가"
    if cat == "데이터 누락 문의":
        return f"센서 데이터 누락 확인 ({eq_id})" if eq_id else "데이터 누락 문의"
    if cat == "임계치 설정 문의":
        return f"임계치 변경 요청 ({alarm_code})" if alarm_code else "임계치 설정 변경 문의"
    if cat == "설비 상태 불일치":
        return f"설비 상태 표시 불일치 ({eq_id})"
    if cat == "권한 문제":
        return "권한 문제 — 접근 불가"
    if cat == "시스템 접속 오류":
        return "FDC 시스템 접속 안됨"
    if cat == "알람 코드 의미 문의":
        return f"{alarm_code} 의미 문의"
    if cat == "VOC 처리 상태 문의":
        return "이전 VOC 처리 상태 확인"
    return "기타 문의"


def main():
    print(f"[build_db] loading {SOT_PATH.relative_to(ROOT)}")
    sot = load_sot()
    print("[build_db] generating CSVs...")
    equipment_rows = build_equipment_master(sot)
    alarm_code_rows = build_alarm_code_master(sot)
    user_rows = build_user_master(sot)
    build_alarm_history(sot, equipment_rows, alarm_code_rows)
    build_voc_history(sot, equipment_rows, user_rows, alarm_code_rows)
    print("[build_db] done.")


if __name__ == "__main__":
    main()
