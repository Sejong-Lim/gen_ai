# FDC-Monitoring AI System — 장애 대응 가이드 (SOP)

> **문서 ID**: troubleshooting_guide
> **버전**: 1.0.0
> **마지막 개정**: 2026-05-12
>
> 본 가이드는 알람 코드별 표준 조치 절차(SOP, Standard Operating Procedure)를 정의합니다. 각 SOP는 알람 코드와 1:N 매핑되며, 알람 상세 화면에서 자동 링크됩니다. 알람 코드 자체의 의미·임계치는 [alarm_code_guide.md](alarm_code_guide.md)를 참조하세요.

---

## SOP 사용 규칙

1. **각 단계의 결과를 기록**하세요. 단계 통과/실패는 VOC 등록 시 첨부됩니다.
2. **단계를 건너뛰지 마세요.** 안전 점검 단계가 우선 배치되어 있습니다.
3. **escalation 조건**에 해당하면 즉시 다음 단계로 가지 말고 escalation 하세요.
4. SOP 절차로 해결 불가 시 [SOP-ESC-001] 벤더 escalation 절차를 따르세요.

---

## SOP-TEMP-001 | 챔버 과열 대응

**적용 알람**: TEMP-C-001, TEMP-H-001
**적용 설비 타입**: CVD, DRY, FUR, RTP
**예상 소요 시간**: 15분 이내 (Critical) / 30분 이내 (High)

### 사전 안전 확인
- 알람 발생 챔버 근처 가스 검출기 상태 확인 (Toxic Gas 동시 검출 여부)
- Toxic Gas 동시 검출 시 즉시 [SOP-GAS-001]로 전환 (EHS 우선)

### 단계별 절차
1. **가스 공급 상태 확인** — 해당 챔버의 process gas MFC setpoint 대비 실제 flow 일치 여부 확인. 차이가 setpoint -10% 이상이면 [SOP-FLOW-001] 병행.
2. **냉각수 유량/온도 확인** — Facility 모니터링 화면에서 해당 설비 냉각수 입출구 압력·온도 확인. 입출구 압력 차가 정상치의 70% 이하면 냉각수 공급 이슈.
3. **히터 출력 확인** — Trend Chart에서 직전 30분 히터 출력값을 확인. setpoint 도달 후에도 히터 출력이 정상치 +20% 지속되면 over-shoot로 판단.
4. **TC(열전대) 응답 확인** — 같은 챔버 내 보조 TC 값과 메인 TC 값의 차이 확인. 차이 5°C 초과면 TC 노화·오결선 의심.
5. **챔버 hold + recipe 정지** — 위 모두 정상이면 챔버 hold 상태에서 idle 후 재가동.
6. **결과 기록** — 위 단계의 통과/실패를 VOC 본문에 기록.

### Escalation 조건
- 1, 2단계 모두 fail (가스·냉각수 동시 이상) → 즉시 팀장 호출
- 3, 4단계로 원인 특정 불가 시 → [SOP-ESC-001]에 따라 벤더 기술지원 요청

---

## SOP-TEMP-002 | 히터 온도 편차 대응

**적용 알람**: TEMP-H-002, TEMP-M-001
**적용 설비 타입**: FUR, RTP, CVD, CTR
**예상 소요 시간**: 30분~1시간

### 단계별 절차
1. **편차 발생 zone 식별** — Trend Chart에서 다중 zone 각각의 온도 추이를 비교. 편차가 가장 큰 zone을 확인.
2. **TC 교차 검증** — 해당 zone의 메인 TC와 보조 TC 값 비교. 5°C 초과 차이 시 TC 자체 이상으로 판단.
3. **히터 출력 확인** — 동일 zone의 히터 출력이 인접 zone 대비 비정상적으로 크거나 작은지 확인. 단선 시 출력이 0 또는 100%로 고정될 수 있음.
4. **보온재 상태 확인** — PM 이력에서 해당 zone의 보온재 교체 일자 확인. 18개월 이상 경과 시 손상 의심.
5. **단기 대책 적용** — 인접 zone 출력 보정으로 임시 대응 (PROC_ENG 승인 필요).
6. **PM 일정 반영** — 영구 조치는 정기 PM 시 TC/히터 교체. [POL-CHG-001]에 따라 신청.

### Escalation 조건
- 2단계 TC 이상 또는 3단계 히터 단선 확인 시 → 라인 정지 영향이 큰 경우 즉시 팀장 호출.

---

## SOP-PRES-001 | 챔버 압력 이상 대응

**적용 알람**: PRES-C-001, PRES-H-001, PRES-M-001
**적용 설비 타입**: CVD, PVD, DRY
**예상 소요 시간**: 15~30분

### 단계별 절차
1. **알람 severity 확인** — Critical이면 챔버 자동 hold 상태. 절대 수동으로 vent 시키지 말고 펌프 상태부터 확인.
2. **터보 펌프 회전수 확인** — 정상 회전수의 95% 이하면 펌프 이슈. [SOP-VAC-002] 병행.
3. **Throttle 밸브 위치 확인** — Trend Chart에서 throttle 위치(0~100%) 추이 확인. 끝단(0% 또는 100%) 고착 시 throttle 이슈.
4. **가스 flow 합 확인** — process 중 모든 MFC의 flow 합이 setpoint 대비 +15% 이상이면 [SOP-FLOW-001] 병행.
5. **챔버 압력 setpoint 변경 응답 테스트** — Idle 상태에서 setpoint를 10% 변경했을 때 도달 시간을 baseline과 비교.
6. **원인 격리 후 재기동** — 원인을 특정하지 못한 경우 챔버 dry-clean 후 재기동.

### Escalation 조건
- 2, 3단계에서 펌프/throttle 하드웨어 이상 → 정비팀 호출
- 4시간 내 동일 알람 재발 → [SOP-ESC-001]

---

## SOP-FLOW-001 | 가스 유량 이상 대응

**적용 알람**: FLOW-H-001, FLOW-W-001, FLOW-M-001
**적용 설비 타입**: CVD, DRY, FUR
**예상 소요 시간**: 15분

### 단계별 절차
1. **가스 잔량 확인** — 해당 라인의 실린더 잔량을 facility 화면에서 확인. 15% 이하면 [AC-GAS-W-001] 동시 발생 여부 확인.
2. **MFC 영점 점검** — gas off 상태에서 MFC 측정값이 0±0.5% 이내인지 확인. 벗어나면 MFC 영점 drift.
3. **필터 차압 확인** — 가스 라인 필터의 입출구 차압이 spec 초과 시 필터 막힘 의심.
4. **밸브 누설 점검** — 해당 가스의 isolation valve 닫음 후 5분간 chamber 압력 변동 측정. 변동 시 밸브 누설 가능성.
5. **MFC 보정** — 필요 시 PROC_ENG 승인 후 MFC 영점/스팬 보정 진행.

### Escalation 조건
- 4단계에서 밸브 누설 확인 시 즉시 isolation 후 정비팀 호출 (Toxic Gas 동반 시 [SOP-GAS-001])

---

## SOP-RF-001 | RF 출력 이상 대응

**적용 알람**: RF-C-001, RF-H-001, RF-W-001
**적용 설비 타입**: CVD, PVD, DRY
**예상 소요 시간**: 20~40분

### 단계별 절차
1. **즉시 RF off 확인** — Critical 알람은 자동 RF off. 수동으로 켜지 마세요.
2. **Reflected/Forward 비율 추이 확인** — Trend Chart에서 직전 1시간 비율 변화 확인.
3. **Matcher tune/load position 확인** — Auto-tune 동작 로그에서 ringing/oscillation 여부 확인. 발생 시 [SOP-RF-002].
4. **전극·챔버 contamination 점검** — 직전 maintenance 이력에서 챔버 cleaning 주기 초과 여부 확인.
5. **케이블·코넥터 점검** — RF 케이블 외관 점검 (탄화·균열). EQ_ENG 자체 점검 가능 범위까지.
6. **챔버 dry-clean 또는 chamber open 결정** — 4단계에서 contamination 의심 시 dry-clean 수행. dry-clean으로도 회복 안되면 chamber open.

### Escalation 조건
- 5단계 케이블 손상 확인 시 정비팀 호출
- 6단계 chamber open 결정 시 PROC_ENG 승인 필수

---

## SOP-RF-002 | RF Matching 불량 조정

**적용 알람**: RF-M-001, RF-W-001
**적용 설비 타입**: CVD, PVD, DRY
**예상 소요 시간**: 15~30분

### 단계별 절차
1. **Auto-tune 재실행** — Matcher의 auto-tune을 강제 재실행. 첫 시도에서 해결되는 경우가 많음.
2. **부하 변동 원인 확인** — recipe 변경, 신규 lot 시작, 챔버 vent 후 첫 가동 등 부하 변동 트리거가 있었는지 확인.
3. **Tune cap 동작 범위 확인** — Trend Chart에서 tune/load cap 위치가 끝단에 도달했는지 확인. 도달했다면 cap 노후 가능성.
4. **Matcher reset** — Matcher 컨트롤러 reset 후 auto-tune 재실행. EQ_ENG 자체 가능.
5. **수동 tune 위치 적용 (PROC_ENG)** — 위 모두 실패 시 PROC_ENG의 승인 하에 수동 tune 위치를 적용.

### Escalation 조건
- 3단계 tune cap 끝단 도달 → 정비팀에 Matcher 점검 요청
- 5단계 수동 tune 위치 적용은 일시적 조치이며, 24시간 이내 PM 일정에 반영해야 함.

---

## SOP-VAC-001 | 챔버 진공 누설 대응

**적용 알람**: VAC-C-001, VAC-H-001
**적용 설비 타입**: CVD, PVD, DRY, HCI, MCI
**예상 소요 시간**: 1~3시간 (누설 위치에 따라 다름)

### 단계별 절차
1. **챔버 isolation** — 영향받은 챔버를 inert gas로 격리 후 다른 챔버 운영 지속 가능성 평가.
2. **Rate of Rise 측정** — 챔버 isolation 상태에서 5분간 압력 상승 속도를 측정. 정상 baseline과 비교.
3. **누설 위치 추정 순서** — viewport → 챔버 door O-ring → feedthrough → gas line 순으로 점검.
4. **He leak test** — 의심 부위에 He 가스 분사 후 RGA 또는 He leak detector로 신호 확인.
5. **부품 교체** — 누설 부위 확인 후 O-ring/viewport 교체. PM 키트 활용.
6. **펌프 다운 & 검증** — 교체 후 base pressure 도달 시간이 baseline 이내인지 검증.

### Escalation 조건
- 3단계까지 누설 위치 미확인 시 [SOP-ESC-001] 벤더 점검 요청
- feedthrough 누설 확인 시 안전 절차상 PROC_ENG 승인 필수

---

## SOP-VAC-002 | 진공 펌프 응답 이상 점검

**적용 알람**: VAC-M-001, VAC-W-001
**적용 설비 타입**: CVD, PVD, DRY
**예상 소요 시간**: 30분~2시간

### 단계별 절차
1. **펌프 회전수 안정 시간 측정** — 펌프 시작부터 정상 회전수 도달까지 시간을 baseline과 비교.
2. **펌프 냉각수 상태 확인** — 입출구 온도차가 정상 (보통 5~10°C) 범위인지 확인. 차이가 작으면 냉각수 유량 부족.
3. **베어링 진동 확인** — [AC-MECH-W-001]과 동반 발생 여부 확인. 동반 시 베어링 마모 진행 의심.
4. **펌프 오일 상태 확인 (드라이 펌프인 경우 N/A)** — 점검 주기 도달 시 교체.
5. **임시 운영 가능성 평가** — 1, 2, 3단계 결과로 단기 운영 가능 여부 판단.

### Escalation 조건
- 2단계 냉각수 이슈 → facility팀 호출
- 3단계 베어링 진행 또는 4시간 내 동일 알람 재발 → 정비팀 PM 일정 앞당김 요청

---

## SOP-COMM-001 | 호스트 통신 단절 대응

**적용 알람**: COMM-H-001, COMM-M-001, COMM-W-001
**적용 설비 타입**: 전 설비
**예상 소요 시간**: 10~30분

### 단계별 절차
1. **EAP 프로세스 상태 확인** — 설비 EAP 컨트롤러의 프로세스가 살아 있는지 확인.
2. **네트워크 연결 확인** — ping 테스트로 EAP-호스트 간 네트워크 도달성 확인.
3. **EAP 재시작 (EQ_ENG 권한)** — 네트워크 정상인데 SECS link만 끊긴 경우 EAP 프로세스 재시작.
4. **수동 운영 모드 전환** — 통신 복구 지연이 30분 이상 예상되면 PROC_ENG 승인 하에 수동 운영 모드 전환.
5. **이력 동기화** — 통신 복구 후 단절 기간 동안의 알람·이벤트·데이터를 호스트에 강제 동기화.

### Escalation 조건
- 2단계 네트워크 자체 이상 → IT/CIM팀 호출
- 4단계 수동 운영 모드는 최대 4시간 이내로 제한 — 이후 [SOP-ESC-001]

---

## SOP-REC-001 | Recipe 다운로드 실패 대응

**적용 알람**: REC-H-001, REC-M-001
**적용 설비 타입**: 전 설비 (계측/검사 제외)
**예상 소요 시간**: 10~20분

### 단계별 절차
1. **Recipe checksum 비교** — MES 등록 recipe와 설비 수신 recipe의 checksum을 비교.
2. **권한 확인** — 다운로드 요청자(설비)의 MES 권한이 유효한지 확인. 권한 만료 시 [POL-ACC-001].
3. **수동 다운로드 재시도** — 설비에서 수동으로 다운로드 재시도 (3회 한정).
4. **Recipe 재등록** — checksum 불일치 지속 시 PROC_ENG가 MES에서 recipe 재등록.
5. **Recipe 버전 강제 동기화** — REC-W-001 (버전 불일치) 동반 발생 시 [FAQ-008]에 따른 수동 동기화.

### Escalation 조건
- 4단계 PROC_ENG 재등록 후에도 실패 → CIM팀 호출

---

## SOP-DOSE-001 | Dose 측정 이상 대응

**적용 알람**: DOSE-C-001, DOSE-H-001
**적용 설비 타입**: HCI, MCI
**예상 소요 시간**: 30분~1시간

### 단계별 절차
1. **Critical 알람 시 즉시 lot hold** — 영향받은 wafer를 lot hold 처리.
2. **Faraday cup contamination 확인** — Faraday cup 측정 raw signal의 noise level이 baseline 대비 +20% 이상이면 contamination 의심.
3. **Beam profile 측정** — beam scan profile의 균일도가 spec 이내인지 확인.
4. **Calibration 절차 실행** — Faraday cup calibration recipe로 측정값 보정 (PROC_ENG 승인).
5. **재측정 wafer 평가** — calibration 후 wafer 1매에 대해 재측정하여 spec 이내 회복 여부 확인.

### Escalation 조건
- 2단계 contamination 확인 시 챔버 cleaning 필요 — 정비팀
- 5단계 회복 실패 시 [SOP-ESC-001]

---

## SOP-GAS-001 | Toxic Gas 검출 대응 (EHS)

**적용 알람**: GAS-C-001
**적용 설비 타입**: CVD, DRY, FUR
**예상 소요 시간**: 즉시 대응 / 후속 점검 2~4시간

### 사전 안전 확인
- **본 SOP는 EHS 절차와 연계됩니다.** 사내 EHS 매뉴얼이 별도로 존재하며, 본 SOP는 FDC 시스템 관점의 절차만 다룹니다.
- **인명 안전 우선** — 검출 농도가 TLV 50%를 초과하면 해당 구역의 인원을 우선 대피시키세요.

### 단계별 절차
1. **즉시 가스 공급 차단** — VMB(Valve Manifold Box)의 manual valve 차단.
2. **EHS 호출** — 사내 EHS 핫라인으로 신고 (사번 + 위치 + 가스 종류 + 검출 농도).
3. **인근 인원 대피 및 환기** — 해당 구역 인원 대피, 배기 강화.
4. **누설 위치 확인 (EHS 입회 하)** — VMB → 라인 → 챔버 inlet 순으로 He leak test.
5. **수리 및 검증** — 누설 부위 수리 후 He leak test 재실시. 통과 시 가스 공급 재개.
6. **사후 보고** — EHS 양식에 따라 사고 보고서 작성.

### Escalation 조건
- 1단계 즉시 차단 후, 검출 농도가 5분 이상 감소하지 않으면 라인 정지.
- **모든 후속 작업은 EHS 입회 하**에 진행해야 합니다.

---

## SOP-GAS-002 | 가스 라인 누설 의심 대응

**적용 알람**: GAS-H-001, GAS-M-001
**적용 설비 타입**: CVD, DRY, FUR
**예상 소요 시간**: 30분~1시간

### 단계별 절차
1. **Toxic Gas 동시 검출 여부 확인** — [GAS-C-001] 동시 발생 시 즉시 [SOP-GAS-001]로 전환.
2. **해당 가스 isolation** — manual valve 또는 EAP에서 해당 가스 라인 isolation.
3. **MFC 입출력 압력 비교** — Trend Chart에서 입력압/출력압 추이 비교. 비정상 차이 구간 확인.
4. **VCR fitting 점검** — 의심 fitting을 시각/촉각으로 점검. 부식·균열 확인.
5. **He leak test** — 의심 부위에 He 분사 후 RGA로 신호 확인.
6. **수리 및 검증** — 부품 교체 후 누설 재측정. baseline 이내 회복 시 운영 재개.

### Escalation 조건
- 1단계 Toxic Gas 동반 시 즉시 [SOP-GAS-001]
- 5단계까지 누설 위치 미확인 시 [SOP-ESC-001]

---

## SOP-HV-001 | 고전압 Trip 대응

**적용 알람**: HV-C-001, HV-H-001
**적용 설비 타입**: HCI, MCI, PVD
**예상 소요 시간**: 30분~2시간

### 단계별 절차
1. **HV off 확인** — Critical 시 자동 off. 수동 켜기 금지.
2. **소스 contamination 점검** — implanter의 경우 소스 챔버 내부 contamination 이력 확인 (정기 cleaning 주기).
3. **HV 케이블 절연 점검** — 절연 저항 측정 (EQ_ENG 자체 가능 범위까지). 정상치 미달 시 케이블 교체.
4. **HV PS ripple 측정** — power supply 출력 ripple이 spec 이내인지 측정.
5. **소스 cleaning 또는 PS 교체** — 원인에 따른 부품 교체. PROC_ENG 승인 필요.
6. **점진적 HV ramp 재기동** — setpoint의 70%부터 단계적으로 ramp 하여 안정성 확인.

### Escalation 조건
- 2단계 소스 cleaning 결정 시 정비팀
- 4단계 PS ripple 이상 확인 시 [SOP-ESC-001]

---

## SOP-CHEM-001 | 케미컬 농도 관리

**적용 알람**: CHEM-H-001, CHEM-W-001
**적용 설비 타입**: WET, POL, CLN, CTR
**예상 소요 시간**: 15~30분

### 단계별 절차
1. **현재 측정 농도 vs spec 비교** — 측정값이 spec의 어느 방향(고농도/저농도)으로 벗어났는지 확인.
2. **Titrator 시약 상태 확인** — 시약 잔량/유효기간 확인. 만료 시 측정 오류 가능.
3. **수동 측정 (재현 확인)** — 별도 측정 장비로 수동 측정하여 titrator 값과 비교.
4. **케미컬 보충 또는 mixing 재실행** — 농도가 낮으면 보충, 비균질이면 mixing 재실행.
5. **재측정 후 운영 재개** — spec 범위 회복 확인.

### Escalation 조건
- 2단계 시약 부족 시 즉시 화학팀 호출
- 3단계 수동 측정과 titrator 값이 5% 이상 차이 시 titrator calibration 필요 — 정비팀

---

## SOP-MECH-001 | 로봇 핸들링 오류 대응

**적용 알람**: MECH-H-001
**적용 설비 타입**: 대부분의 설비 (FUR/RTP 제외)
**예상 소요 시간**: 15~30분

### 단계별 절차
1. **wafer 위치 확인** — 로봇 오류 시점의 wafer 위치(LOAD, EFEM, PROCESS chamber 등)를 EAP 로그로 확인.
2. **wafer 회수 절차** — 안전한 위치로 wafer 수동 회수 (FIELD 또는 EQ_ENG).
3. **Vacuum chuck 흡착 점검** — 흡착 압력이 정상치 이내인지 확인. 부족하면 진공 라인 점검.
4. **End-effector 정렬 점검** — 로봇 end-effector의 미세 정렬이 spec 이내인지 확인.
5. **Reset 및 dry run** — 로봇 reset 후 wafer 없이 dry run으로 정상 동작 확인.
6. **운영 재개** — 정상 동작 확인 후 운영 재개.

### Escalation 조건
- 4단계 정렬 이슈 확인 시 정비팀
- 동일 lot에서 2회 이상 반복 시 [SOP-ESC-001]

---

## SOP-MECH-002 | 슬릿밸브 동작 이상 점검

**적용 알람**: MECH-M-001
**적용 설비 타입**: CVD, PVD, DRY, HCI, MCI
**예상 소요 시간**: 20~40분

### 단계별 절차
1. **공압 라인 압력 확인** — 슬릿밸브 공급 공압 (보통 5~7 bar)이 정상 범위인지 확인.
2. **밸브 동작 시간 측정** — open/close 명령 후 응답 시간을 Trend Chart로 확인. spec과 비교.
3. **위치 센서 신호 확인** — open/close limit switch 신호 정상 여부 확인.
4. **수동 동작 테스트** — 안전 절차에 따라 수동 open/close 동작 테스트.
5. **PM 일정 반영** — 동작 시간이 spec + 0.5초 이상 지속 시 PM 시 부품 교체 요청.

### Escalation 조건
- 1단계 공압 이상 → facility팀
- 3단계 위치 센서 이상 → 정비팀

---

## SOP-ESC-001 | 벤더 Escalation 절차

**적용 상황**:
- 내부 SOP로 원인 특정 불가
- 벤더 전용 진단 도구 필요
- HW 교체 결정 필요
- KB 범위 밖 문의 ([POL-SCOPE-001] 참조)

### 단계별 절차
1. **사내 escalation 1차 — 팀장 보고** — 팀장에게 현 상황·시도한 SOP 단계·결과 요약 보고.
2. **벤더 기술지원 티켓 발행** — 사내 CIM 포털에서 벤더 기술지원 티켓 발행 — 다음 정보 첨부:
   - 알람 코드와 발생 패턴
   - 시도한 SOP 단계와 결과
   - 관련 Trend Chart 캡처 (직전 24시간)
   - 설비 EAP 로그 (직전 1시간)
3. **벤더 응답 대기 및 사내 운영 결정** — 응답 대기 중 사내 운영(다른 챔버 활용, lot 분산)을 PROC_ENG가 결정.
4. **벤더 출동 시 사내 입회** — EQ_ENG 또는 정비팀이 반드시 입회.
5. **조치 완료 후 사후 보고** — 벤더 보고서를 사내에 보관하고 동일 사례 재발 방지 가이드 업데이트.

### Escalation Tier
- **Tier 1**: 24시간 이내 응답
- **Tier 2 (Critical)**: 4시간 이내 응답 — Critical 알람이거나 라인 정지 영향 시
- **Tier 3 (Onsite)**: 24시간 이내 출동

---

## SOP-ESC-002 | 야간/주말 비상 대응

**적용 상황**: 정규시간(09:00-18:00) 외 Critical 알람 발생

### 단계별 절차
1. **즉시 야간조 EQ_ENG 1차 대응** — 자동 호출.
2. **대응 불가 판단 시 호출 트리 실행**:
   - 1차: 야간조 EQ_ENG (해당 공정팀)
   - 2차: 해당 공정팀 팀장 (15분 이내 응답 없을 시)
   - 3차: 공정 PM (팀장 응답 불가 시)
   - 4차: 벤더 Tier 2 escalation
3. **임시 운영 결정** — 라인 정지 영향 평가 후 임시 운영/정지 결정 (3차 이상 권한 필요).
4. **익일 보고** — 정규시간 시작 후 4시간 이내 상세 보고서 작성.

자세한 호출 트리는 [POL-NIGHT-001]을 참조하세요.
