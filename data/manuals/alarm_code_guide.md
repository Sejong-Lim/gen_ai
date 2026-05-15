# FDC-Monitoring AI System — 알람 코드 설명서

> **문서 ID**: alarm_code_guide
> **버전**: 1.0.0
> **마지막 개정**: 2026-05-12
>
> 본 문서는 FDC-Monitoring AI System이 발생시키는 알람 코드 42종의 의미·임계치·발생 조건·일반적 원인을 정의합니다. 단계별 조치 절차는 각 항목 끝의 SOP 링크를 따라 [장애 대응 가이드](troubleshooting_guide.md)를 참조하세요.

---

## 1. 알람 코드 명명 규칙

알람 코드는 `{Category}-{Severity}-{Sequence}` 형식입니다.

- **Category** (12종): TEMP / PRES / FLOW / RF / VAC / GAS / HV / DOSE / CHEM / COMM / REC / MECH
- **Severity** (5단계):
  - `C` Critical — 즉시 설비 정지 및 escalation
  - `H` High — 자동 hold, 1차 대응 필요
  - `M` Medium — 진행 계속, 다음 Lot 전 확인
  - `W` Warning — 추이 모니터링
  - `I` Info — 정보성 이벤트, 조치 불필요

---

## 2. TEMP — 온도 알람

### AC-TEMP-C-001 | 챔버 과열 Critical (TEMP-C-001)

- **의미**: 챔버 온도가 recipe setpoint + 50°C 초과 또는 절대값 380°C 초과로 즉시 인터록 작동.
- **임계치**: 챔버 온도 > recipe setpoint + 50°C 또는 절대값 380°C 초과
- **일반적 원인**: 냉각수 차단 / 히터 단락 / 센서 오결선
- **적용 설비 타입**: CVD, DRY, FUR, RTP
- **조치 절차**: [SOP-TEMP-001]

### AC-TEMP-H-001 | 챔버 과열 High (TEMP-H-001)

- **의미**: 챔버 온도가 recipe setpoint를 20°C 이상 초과하여 자동 hold.
- **임계치**: 챔버 온도 > recipe setpoint + 20°C (예: setpoint 300°C 기준 320°C 초과)
- **일반적 원인**: 가스 유량 부족으로 인한 발열 누적 / 냉각수 유량 저하 / 히터 over-shoot
- **적용 설비 타입**: CVD, DRY, FUR, RTP
- **조치 절차**: [SOP-TEMP-001]
- **관련 FAQ**: 본 코드와 함께 자주 묻는 사항은 별도 정의 없음.

### AC-TEMP-H-002 | 히터 Zone 편차 High (TEMP-H-002)

- **의미**: 다중 zone furnace에서 zone 간 온도차가 허용 범위를 초과.
- **임계치**: 다중 zone furnace에서 zone 간 온도차 > 8°C
- **일반적 원인**: zone 히터 단선 / TC 노화 / 보온재 손상
- **적용 설비 타입**: FUR
- **조치 절차**: [SOP-TEMP-002]

### AC-TEMP-M-001 | 가열 속도 이상 (TEMP-M-001)

- **의미**: ramp rate가 recipe 대비 허용 편차 초과.
- **임계치**: ramp rate가 recipe 대비 ±15% 초과 편차
- **일반적 원인**: 히터 출력 저하 / TC 응답 지연
- **적용 설비 타입**: CVD, FUR, RTP, CTR
- **조치 절차**: [SOP-TEMP-002]

### AC-TEMP-W-001 | 챔버 저온 Warning (TEMP-W-001)

- **의미**: Idle 상태 챔버 온도가 setpoint 대비 -10°C 이하로 떨어진 경고성 표시.
- **임계치**: Idle 상태 챔버 온도 < setpoint - 10°C
- **일반적 원인**: 대기열 길어짐 / 유휴 상태에서 자연 냉각
- **적용 설비 타입**: CVD, DRY, FUR
- **조치 절차**: *본 코드는 별도 SOP가 없습니다.* 운영상 자연스러운 idle 동작에 가까우며, 동일 Warning이 반복되거나 다음 Lot 시작 시 도달 지연이 함께 보고되면 [SOP-TEMP-002]를 참조하여 히터 출력을 점검하세요.

---

## 3. PRES — 압력 알람

### AC-PRES-C-001 | 챔버 압력 Critical (PRES-C-001)

- **의미**: process pressure가 setpoint 대비 30% 이상 이탈하여 즉시 hold.
- **임계치**: process pressure가 setpoint 대비 ±30% 초과
- **일반적 원인**: TM(Transfer Module) 밸브 고착 / 펌프 정지 / MFC 폭주
- **적용 설비 타입**: CVD, PVD, DRY
- **조치 절차**: [SOP-PRES-001]

### AC-PRES-H-001 | 챔버 압력 High (PRES-H-001)

- **의미**: 공정 압력이 setpoint 대비 +15% 초과.
- **임계치**: process pressure가 setpoint 대비 +15% 초과
- **일반적 원인**: 배기 throttle 동작 불량 / 가스 과주입
- **적용 설비 타입**: CVD, PVD, DRY
- **조치 절차**: [SOP-PRES-001]

### AC-PRES-M-001 | 압력 변동 이상 (PRES-M-001)

- **의미**: 압력이 setpoint 근처에서 비정상적으로 진동.
- **임계치**: 30초 이동표준편차 > setpoint × 5%
- **일반적 원인**: 가스 라인 진동 / throttle 미세진동
- **적용 설비 타입**: CVD, PVD, DRY
- **조치 절차**: [SOP-PRES-001]

### AC-PRES-W-001 | 압력 센서 응답 지연 (PRES-W-001)

- **의미**: setpoint 변경 후 압력 도달이 baseline 대비 느림.
- **임계치**: setpoint 변경 후 90% 도달 시간 > 7초
- **일반적 원인**: 바라트론 노화
- **적용 설비 타입**: CVD, PVD, DRY
- **조치 절차**: *본 코드에 매핑된 표준 SOP는 없습니다.* 일반적으로 정기 PM(Preventive Maintenance) 주기에 바라트론 교체로 해결되며, 동일 Warning이 4시간 내 5회 이상 반복되면 [SOP-ESC-001]을 따라 벤더 escalation을 검토하세요.

---

## 4. FLOW — 가스 유량 알람

### AC-FLOW-H-001 | 가스 유량 과다 (FLOW-H-001)

- **의미**: MFC 측정 유량이 setpoint를 10% 이상 초과.
- **임계치**: MFC 측정값이 setpoint 대비 +10% 초과
- **일반적 원인**: MFC 영점 drift / 밸브 누설
- **적용 설비 타입**: CVD, DRY, FUR
- **조치 절차**: [SOP-FLOW-001]

### AC-FLOW-W-001 | 가스 유량 부족 (FLOW-W-001)

- **의미**: MFC 측정 유량이 setpoint 대비 10% 미달.
- **임계치**: MFC 측정값이 setpoint 대비 -10% 미달
- **일반적 원인**: 가스 잔량 부족 / 필터 막힘
- **적용 설비 타입**: CVD, DRY, FUR
- **조치 절차**: [SOP-FLOW-001]

### AC-FLOW-M-001 | MFC 응답 이상 (FLOW-M-001)

- **의미**: MFC가 setpoint 변경에 느리게 반응.
- **임계치**: setpoint 변경 후 ±5% 도달 시간 > 3초
- **일반적 원인**: MFC controller 노후 / 통신 지연
- **적용 설비 타입**: CVD, DRY
- **조치 절차**: [SOP-FLOW-001]

---

## 5. RF — RF 출력 알람

### AC-RF-C-001 | RF Reflected Power Critical (RF-C-001)

- **의미**: 반사파 비율이 위험 수준을 초과하여 즉시 RF off.
- **임계치**: Reflected / Forward 비율 > 30%
- **일반적 원인**: Matcher 단락 / 전극 contamination
- **적용 설비 타입**: CVD, PVD, DRY
- **조치 절차**: [SOP-RF-001]

### AC-RF-H-001 | RF Forward Power 편차 High (RF-H-001)

- **의미**: RF Forward Power가 recipe setpoint와 큰 차이.
- **임계치**: Forward Power가 recipe 대비 ±10% 초과
- **일반적 원인**: Generator 출력 저하 / 케이블 손상
- **적용 설비 타입**: CVD, PVD, DRY
- **조치 절차**: [SOP-RF-001]

### AC-RF-M-001 | RF Matching 불량 (RF-M-001)

- **의미**: Auto-tune 후에도 반사파가 잔존.
- **임계치**: Auto-tune 후 reflected > 5% 잔존
- **일반적 원인**: 부하 변동 / tune cap 노후
- **적용 설비 타입**: CVD, PVD, DRY
- **조치 절차**: [SOP-RF-002]

### AC-RF-W-001 | RF 출력 변동 Warning (RF-W-001)

- **의미**: RF 출력이 평균 대비 미세하게 진동.
- **임계치**: 60초 표준편차 > 평균 × 3%
- **일반적 원인**: 부하 매칭 미세조정 부족
- **적용 설비 타입**: CVD, PVD, DRY
- **조치 절차**: [SOP-RF-002]

---

## 6. VAC — 진공 알람

### AC-VAC-C-001 | 챔버 진공 누설 Critical (VAC-C-001)

- **의미**: base pressure에 도달하지 못하거나 leak rate가 위험 수준 초과.
- **임계치**: base pressure 도달 실패 또는 leak rate > 1e-5 Torr·L/s
- **일반적 원인**: O-ring 손상 / viewport crack / feedthrough 누설
- **적용 설비 타입**: CVD, PVD, DRY, HCI, MCI
- **조치 절차**: [SOP-VAC-001]

### AC-VAC-H-001 | 진공도 미달 High (VAC-H-001)

- **의미**: base pressure가 목표값에 도달하지 못함.
- **임계치**: base pressure > 5e-6 Torr (목표 1e-6 Torr)
- **일반적 원인**: 펌프 성능 저하 / 챔버 outgassing
- **적용 설비 타입**: CVD, PVD, DRY, HCI, MCI
- **조치 절차**: [SOP-VAC-001]

### AC-VAC-M-001 | 진공 펌프 응답 이상 (VAC-M-001)

- **의미**: 터보 펌프 회전수 안정화에 평소보다 오래 걸림.
- **임계치**: 터보 펌프 회전수 안정화 시간 > 정상 +30%
- **일반적 원인**: 베어링 노후 / 냉각수 온도 상승
- **적용 설비 타입**: CVD, PVD, DRY
- **조치 절차**: [SOP-VAC-002]

### AC-VAC-W-001 | 진공 회복 지연 (VAC-W-001)

- **의미**: 벤트 후 base pressure 도달 시간이 baseline 대비 길어짐.
- **임계치**: 벤트→base pressure 도달 시간이 baseline + 20% 초과
- **일반적 원인**: 펌프 성능 저하 초기 증상
- **적용 설비 타입**: CVD, PVD, DRY
- **조치 절차**: [SOP-VAC-002]

---

## 7. GAS — 가스(누설/잔량) 알람

### AC-GAS-C-001 | Toxic Gas 검출 Critical (GAS-C-001)

- **의미**: 라인 외부 가스 검출기에서 위험 가스 농도 감지. EHS 영향.
- **임계치**: 라인 가스 검출기 농도가 TLV(Threshold Limit Value)의 50% 초과
- **일반적 원인**: 배관 누설 / VMB 밸브 불완전 잠금
- **적용 설비 타입**: CVD, DRY, FUR
- **조치 절차**: [SOP-GAS-001] (EHS 절차 연계)

### AC-GAS-H-001 | 가스 라인 누설 의심 High (GAS-H-001)

- **의미**: MFC 입출력 압력 차와 flow 측정값이 불일치하여 누설 의심.
- **임계치**: MFC 입출력 압력 차 이상 + flow setpoint 불일치
- **일반적 원인**: VCR fitting 풀림 / 라인 부식
- **적용 설비 타입**: CVD, DRY, FUR
- **조치 절차**: [SOP-GAS-002]

### AC-GAS-M-001 | 가스 압력 이상 (GAS-M-001)

- **의미**: 공급 가스 압력이 정상 범위를 벗어남.
- **임계치**: 공급압력이 spec 대비 ±15% 초과
- **일반적 원인**: regulator 노후
- **적용 설비 타입**: CVD, DRY, FUR
- **조치 절차**: [SOP-GAS-002]

### AC-GAS-W-001 | 가스 잔량 부족 Warning (GAS-W-001)

- **의미**: 실린더 잔량이 교체 임계를 하회.
- **임계치**: 실린더 잔량 < 15%
- **일반적 원인**: 정기 교체 임박
- **적용 설비 타입**: CVD, DRY, FUR, RTP
- **조치 절차**: 본 코드는 별도 SOP가 없으며, 실린더 교체 일정 수립 절차는 [FAQ-004]를 참조하세요. 잔량 10% 이하로 떨어지면 자동으로 추가 알람이 발생하지 않으므로 즉시 가스 공급팀에 교체 요청을 해야 합니다.

---

## 8. HV — 고전압 알람

### AC-HV-C-001 | 고전압 Trip Critical (HV-C-001)

- **의미**: Beam current 또는 extraction voltage가 안전 한계 초과로 인터록 작동.
- **임계치**: Beam current 또는 extraction voltage가 안전 한계 초과로 인터록 작동
- **일반적 원인**: arcing / 소스 contamination
- **적용 설비 타입**: HCI, MCI, PVD
- **조치 절차**: [SOP-HV-001]

### AC-HV-H-001 | 고전압 변동 High (HV-H-001)

- **의미**: HV 안정화 후 출력이 비정상적으로 진동.
- **임계치**: HV 안정화 후 30초 표준편차 > 0.5%
- **일반적 원인**: power supply ripple 증가 / 케이블 절연 열화
- **적용 설비 타입**: HCI, MCI, PVD
- **조치 절차**: [SOP-HV-001]

### AC-HV-W-001 | 고전압 RAMP 지연 (HV-W-001)

- **의미**: HV가 setpoint까지 ramp 되는 시간이 늘어남.
- **임계치**: 0→setpoint ramp time이 baseline 대비 +20%
- **일반적 원인**: HV PS 노후
- **적용 설비 타입**: HCI, MCI, PVD
- **조치 절차**: *본 코드에 매핑된 SOP는 정의되어 있지 않습니다.* 일반적으로 PM 주기에 HV PS 성능 점검으로 해결되며, ramp 지연이 baseline +40%를 초과하면 [SOP-ESC-001]에 따라 벤더 escalation 후 PS 교체 검토가 필요합니다.

---

## 9. DOSE — 이온주입 Dose 알람

### AC-DOSE-C-001 | Dose 측정값 범위 초과 Critical (DOSE-C-001)

- **의미**: 측정 dose가 recipe spec 범위를 벗어남 — 즉시 hold.
- **임계치**: 측정 dose가 recipe spec의 ±5% 초과
- **일반적 원인**: Faraday cup 오염 / beam profile shift
- **적용 설비 타입**: HCI, MCI
- **조치 절차**: [SOP-DOSE-001]

### AC-DOSE-H-001 | Dose 균일도 High (DOSE-H-001)

- **의미**: wafer 내 dose 편차가 spec 초과.
- **임계치**: wafer 내 dose 균일도 (1σ) > 1.5%
- **일반적 원인**: beam scan profile drift / Faraday 측정 오차
- **적용 설비 타입**: HCI, MCI
- **조치 절차**: [SOP-DOSE-001]

### AC-DOSE-W-001 | Dose 측정 지연 Warning (DOSE-W-001)

- **의미**: post-implant dose 측정이 평소보다 늦게 완료.
- **임계치**: post-implant 측정 완료 시간 > baseline + 5초
- **일반적 원인**: measurement queue 적체
- **적용 설비 타입**: HCI, MCI
- **조치 절차**: *본 코드는 측정 시스템의 부하 변동에 따른 자연스러운 변동을 포함하므로 표준 SOP가 없습니다.* 지속적 발생 시 측정 큐 길이를 확인하고 운영상 lot 분산이 필요하면 운영팀에 문의하세요.

---

## 10. CHEM — 케미컬 알람

### AC-CHEM-H-001 | 케미컬 농도 이상 (CHEM-H-001)

- **의미**: 측정 농도가 spec 범위를 벗어남.
- **임계치**: titrator 측정 농도가 spec ±2% 초과
- **일반적 원인**: mixing 불량 / 센서 calibration 노후
- **적용 설비 타입**: WET, POL, CLN
- **조치 절차**: [SOP-CHEM-001]

### AC-CHEM-W-001 | 케미컬 보충 필요 Warning (CHEM-W-001)

- **의미**: 케미컬 탱크 잔량이 임계 이하.
- **임계치**: 탱크 잔량 < 20%
- **일반적 원인**: 사용량 증가
- **적용 설비 타입**: WET, POL, CLN, CTR
- **조치 절차**: [SOP-CHEM-001]

---

## 11. COMM — 통신 알람

### AC-COMM-H-001 | EAP 통신 단절 High (COMM-H-001)

- **의미**: 설비 EAP와 호스트(MES/FDC) 간 link 단절.
- **임계치**: EAP-호스트 link 60초 이상 단절
- **일반적 원인**: 네트워크 스위치 이슈 / EAP 프로세스 hang
- **적용 설비 타입**: 전 설비
- **조치 절차**: [SOP-COMM-001]

### AC-COMM-M-001 | SECS/GEM 응답 지연 (COMM-M-001)

- **의미**: 호스트의 SECS 요청에 설비가 늦게 응답.
- **임계치**: S6F11 응답 시간 > 5초
- **일반적 원인**: host load 증가 / buffer overflow
- **적용 설비 타입**: 전 설비
- **조치 절차**: [SOP-COMM-001]

### AC-COMM-W-001 | 호스트 통신 재시도 Warning (COMM-W-001)

- **의미**: T3 timeout이 발생했으나 자동 재시도로 복구.
- **임계치**: T3 timeout 발생 (재시도로 복구됨)
- **일반적 원인**: 네트워크 미세 지연
- **적용 설비 타입**: 전 설비
- **조치 절차**: [SOP-COMM-001]

### AC-COMM-W-002 | 센서 통신 일시 단절 (COMM-W-002)

- **의미**: 특정 SVID 데이터가 짧은 시간 결손.
- **임계치**: 특정 SVID 데이터 결손 < 3초
- **일반적 원인**: DAQ 모듈 jitter
- **적용 설비 타입**: CVD, PVD, DRY, FUR, RTP, HCI, MCI
- **조치 절차**: *본 코드는 단발성 경고로 별도 SOP가 없습니다.* 동일 SVID에서 시간당 10회 이상 반복되면 [FAQ-003]을 참조해 DAQ 모듈 점검 VOC를 등록하세요.

---

## 12. REC — Recipe 알람

### AC-REC-H-001 | Recipe 다운로드 실패 High (REC-H-001)

- **의미**: MES → 설비로의 recipe 전송이 반복적으로 실패.
- **임계치**: MES → 설비 recipe 다운로드 3회 연속 실패
- **일반적 원인**: recipe checksum 불일치 / 권한 만료
- **적용 설비 타입**: 전 설비 (계측/검사 제외)
- **조치 절차**: [SOP-REC-001]

### AC-REC-M-001 | Recipe 파라미터 검증 실패 (REC-M-001)

- **의미**: recipe의 파라미터 값이 spec 범위를 벗어나거나 필수 필드 누락.
- **임계치**: 파라미터 spec 범위 초과 또는 필수 필드 누락
- **일반적 원인**: recipe 편집 오류
- **적용 설비 타입**: 전 설비 (계측/검사 제외)
- **조치 절차**: [SOP-REC-001]

### AC-REC-W-001 | Recipe 버전 불일치 Warning (REC-W-001)

- **의미**: 설비 실행 중 recipe 버전이 MES 등록 최신 버전과 다름.
- **임계치**: 설비 실행 recipe 버전 ≠ MES 등록 latest version
- **일반적 원인**: 버전 동기화 지연
- **적용 설비 타입**: 전 설비 (계측/검사 제외)
- **조치 절차**: [SOP-REC-001] 및 [FAQ-008]

---

## 13. MECH — 기계 동작 알람

### AC-MECH-H-001 | 로봇 핸들링 오류 High (MECH-H-001)

- **의미**: EFEM 로봇이 wafer 위치 파악 또는 transfer에 실패.
- **임계치**: EFEM 로봇 wafer mapping 또는 transfer 실패
- **일반적 원인**: wafer 위치 이상 / vacuum chuck 흡착 불량
- **적용 설비 타입**: 대부분의 설비 (FUR/RTP 제외)
- **조치 절차**: [SOP-MECH-001]

### AC-MECH-M-001 | 슬릿밸브 동작 이상 (MECH-M-001)

- **의미**: 슬릿밸브 open/close 시간이 spec 초과.
- **임계치**: open/close 시간 > spec + 0.5초
- **일반적 원인**: 공압 라인 압력 저하 / 센서 노후
- **적용 설비 타입**: CVD, PVD, DRY, HCI, MCI
- **조치 절차**: [SOP-MECH-002]

### AC-MECH-W-001 | 진동 센서 경고 (MECH-W-001)

- **의미**: 회전부 진동이 baseline 대비 증가.
- **임계치**: 베어링 진동 RMS > baseline × 1.5
- **일반적 원인**: 베어링 마모 초기
- **적용 설비 타입**: CVD, PVD, DRY, POL
- **조치 절차**: *본 코드에 매핑된 SOP가 없습니다.* 정기 PM 시 베어링 상태를 추가 점검하도록 PM 체크리스트에 반영하는 것이 권장됩니다. 진동 RMS가 baseline × 2.0 초과로 도달하면 [SOP-ESC-001]을 따라 벤더 점검을 요청하세요.

---

## 부록 A. 카테고리별 코드 빠른 참조

| Category | Critical | High | Medium | Warning |
|---|---|---|---|---|
| TEMP | TEMP-C-001 | TEMP-H-001, TEMP-H-002 | TEMP-M-001 | TEMP-W-001 |
| PRES | PRES-C-001 | PRES-H-001 | PRES-M-001 | PRES-W-001 |
| FLOW | — | FLOW-H-001 | FLOW-M-001 | FLOW-W-001 |
| RF | RF-C-001 | RF-H-001 | RF-M-001 | RF-W-001 |
| VAC | VAC-C-001 | VAC-H-001 | VAC-M-001 | VAC-W-001 |
| GAS | GAS-C-001 | GAS-H-001 | GAS-M-001 | GAS-W-001 |
| HV | HV-C-001 | HV-H-001 | — | HV-W-001 |
| DOSE | DOSE-C-001 | DOSE-H-001 | — | DOSE-W-001 |
| CHEM | — | CHEM-H-001 | — | CHEM-W-001 |
| COMM | — | COMM-H-001 | COMM-M-001 | COMM-W-001, COMM-W-002 |
| REC | — | REC-H-001 | REC-M-001 | REC-W-001 |
| MECH | — | MECH-H-001 | MECH-M-001 | MECH-W-001 |
