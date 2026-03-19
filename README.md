# Image Grid Viewer

Version: `1.2`

대용량 이미지를 열고, 전역 그리드(Global Grid) 기준으로 셀을 탐색하며, 최대 2개의 ROI(Region of Interest)를 지정해 관심 영역만 정확하게 확인할 수 있는 데스크톱 뷰어입니다.

## 주요 기능
- 큰 이미지 파일 열기
- 마우스 휠 확대/축소
- 휠 클릭 드래그 패닝
- 전역 `Cols`, `Rows` 기준 셀 선택
- `Cell X`, `Cell Y` 좌표 입력으로 셀 직접 조회
- `Unselect`로 선택 해제
- 라벨 표시 On/Off
- 라벨 크기 및 색상 변경
- ROI 1, ROI 2를 점 2개 클릭으로 지정
- ROI 좌표를 `Left / Top / Right / Bottom` 값으로 직접 입력
- 두 점 기준 Crop
- 선택 셀 확대 보기 및 이미지 저장

## 요구 환경
- Python `3.11+`
- Windows 권장

## 설치
```powershell
cd C:\codex
python -m pip install -e .
```

## 실행
```powershell
cd C:\codex
python -m app.main
```

## EXE 빌드
프로젝트에 포함된 스크립트로 빌드:

```powershell
cd C:\codex
Set-ExecutionPolicy -Scope Process Bypass
.\build_exe.ps1
```

직접 PyInstaller로 빌드:

```powershell
cd C:\codex
python -m pip install --user pyinstaller
if (Test-Path .\dist\ImageGridViewer.exe) { Remove-Item .\dist\ImageGridViewer.exe -Force }
python -m PyInstaller --noconfirm --clean --onefile --windowed --name ImageGridViewer `
  --exclude-module numpy `
  --exclude-module numpy_distutils `
  --exclude-module matplotlib `
  --exclude-module tkinter `
  --exclude-module unittest `
  --exclude-module pytest `
  --exclude-module PIL.ImageQt `
  --exclude-module PIL.ImageTk `
  --exclude-module PIL.ImageGrab `
  .\app\main.py
```

정상 빌드 시 실행 파일은 `C:\codex\dist\ImageGridViewer.exe`에 생성됩니다.

## 사용 방법
1. `Open Image...`로 이미지를 엽니다.
2. `Cols`, `Rows`를 설정합니다. 이 값은 ROI별 로컬 설정이 아니라 전체 이미지 기준 전역 그리드입니다.
3. 셀을 선택하는 방법은 두 가지입니다.
   - 좌측 이미지에서 셀을 직접 클릭
   - `Cell X`, `Cell Y` 입력 후 `Apply Selection`
4. 선택을 해제하려면 `Unselect`를 누릅니다.
5. 라벨 가시성은 `Show Labels`로 켜고 끌 수 있습니다.
6. ROI는 두 가지 방식으로 지정할 수 있습니다.
   - `Define ROI 1`, `Define ROI 2` 클릭 후 좌상단 점과 우하단 점을 순서대로 클릭
   - ROI 입력 영역에 `Left / Top / Right / Bottom` 값을 넣고 적용
7. Crop도 두 점 방식으로 지정합니다.
   - `Crop Mode` 진입
   - 좌상단 점, 우하단 점 클릭
   - `Apply Crop` 또는 `Cancel Crop`
8. 우하단 확대 뷰에서 슬라이더로 배율을 조절하고, `Save`로 현재 선택 셀 이미지를 저장합니다.

## 전역 그리드 예시
ROI가 2개이고 전체 설정이 `Cols = 6`, `Rows = 2`라면, 번호는 ROI별로 끊기지 않고 전체 기준으로 이어집니다.

```text
1  2  3 | 4  5  6
7  8  9 | 10 11 12
```

즉 `X, Y` 입력은 항상 전체 범위에서 단 하나의 셀만 가리킵니다.

## 조작 요약
- 휠 스크롤: 확대/축소
- 휠 클릭 드래그: 화면 이동
- 좌클릭: 셀 선택, ROI 점 지정, Crop 점 지정

## 프로젝트 구조
```text
app/
  core/      # 격자 계산, 셀 경계 계산
  models/    # 앱 상태 모델
  ui/        # 메인 윈도우, 캔버스, 확대 패널
README.md
Requirement.MD
pyproject.toml
ImageGridViewer.spec
build_exe.ps1
```

## 참고
- EXE가 실행 중이면 빌드가 실패할 수 있습니다.
- 탐색기 미리보기, 백신, 실시간 보호가 EXE 파일을 점유하면 PyInstaller 빌드가 실패할 수 있습니다.
- 상세 요구사항과 진행 체크는 `Requirement.MD`에 정리되어 있습니다.
