# golden

Golden files for `backend/app/core/predict` (SPEC §8.3): fixed-seed inputs with committed expected outputs. They guarantee the prediction core stays **pure** (no server/simulator coupling) and bit-reproducible — CI fails on any drift.

core/predict 골든파일. 고정 시드 입력에 대한 기대 출력을 커밋해 순수 모듈 보증과 재현성을 지킨다. 엔진 교체(v1/v2/v3) 시 하류 출력 불변성 검증에도 사용된다(§3.7).
