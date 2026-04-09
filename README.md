# 🖼️ Image Grid Viewer

<p align="center">
  <a href="#-english-version">English</a> | <a href="#-한국어-버전">한국어</a>
</p>

---

## 🇺🇸 English Version

![header](https://capsule-render.vercel.app/render?type=wave&color=auto&height=200&section=header&text=Image%20Grid%20Viewer&fontSize=70)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/PySide6-6.7+-41CD52?style=for-the-badge&logo=qt&logoColor=white" />
  <img src="https://img.shields.io/badge/Pillow-10.0+-90422d?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" />
</p>

### 📝 Project Overview
**Image-Grid-Viewer** is a desktop application designed to open high-resolution images and precisely navigate or extract specific cells based on a **Global Grid** system. It supports up to two Regions of Interest (ROI) for continuous labeling and individual cell exporting, and now uses partial loading for large images instead of keeping the full original in a single GUI bitmap.

### ✨ Key Features
#### 1. Global Grid & Navigation
- **Global Coordinate System**: Utilizes a synchronized `Cols` and `Rows` system where cell indexing remains continuous even across separated ROIs.
- **Precise Selection**: Supports selecting single cells via mouse clicks or by directly entering `Cell X, Y` coordinates.
- **Interactive Canvas**: Provides smooth zooming via the mouse wheel and free panning by dragging with the middle mouse button.
- **Large Image Mode**: Uses viewport-based partial rendering so very large source images can be opened more safely than the old full-frame loading approach.

#### 2. Region Selection (ROI & Crop)
- **ROI Configuration**: Set up to two interest regions by clicking two points or entering numerical coordinates (L/T/R/B).
- **Accurate Cropping**: Precise area extraction using a two-point coordinate system rather than simple freehand dragging.

#### 3. Visualization & Export
- **Customizable Labels**: Real-time adjustment of grid label visibility, font scale (50% to 300%), and color.
- **Zoom View & Save**: View selected cells in a dedicated panel with up to 800% magnification and export them instantly as image files (PNG, JPG, BMP).

### 🛠 Tech Stack
- **Language**: Python 3.10+
- **GUI Framework**: PySide6 (Qt for Python)
- **Image Processing**: Pillow
- **Executable Build**: PyInstaller

### 🚀 Getting Started
#### Installation
```powershell
# Clone the repository
git clone [https://github.com/Cobluesky/Image-Grid-Viewer.git](https://github.com/Cobluesky/Image-Grid-Viewer.git)
cd Image-Grid-Viewer

# Create and activate a virtual environment
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -e .
```

#### Running the App
```powershell
python -m app.main
```

#### Building Executable (EXE)
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_exe.ps1
```

#### Building Executable (One Directory)
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_onedir.ps1
```

### 📂 Project Structure
```text
app/
  ├── core/      # Grid calculation and coordinate transformation logic
  ├── models/    # AppState and image metadata management
  └── ui/        # Main window, canvas, and zoom panel UI
pyproject.toml   # Project configuration and dependencies
build_exe.ps1    # One-file build script
build_onedir.ps1 # One-directory build script
pyinstaller_runtime_env.py # Runtime hook that isolates bundled Qt from conda paths
```

### 📄 License
This project is licensed under the **MIT License**.

### 👤 Author (Contact)
**Shin Ha-neul**
- 📧 Email: [habuhamo900@gmail.com](mailto:habuhamo900@gmail.com)
- 🔗 GitHub: [@Cobluesky](https://github.com/Cobluesky)

---

## 🇰🇷 한국어 버전

![header](https://capsule-render.vercel.app/render?type=soft&color=auto&height=200&text=이미지%20그리드%20뷰어&fontSize=70)

<p align="center">
  <img src="https://img.shields.io/badge/Language-Korean-blue?style=for-the-badge&logo=language" />
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/PySide6-6.7+-41CD52?style=for-the-badge&logo=qt&logoColor=white" />
</p>

### 📝 프로젝트 개요
**Image-Grid-Viewer**는 고해상도 이미지를 열고, 전역 그리드(Global Grid) 시스템을 기반으로 특정 셀을 정밀하게 탐색하거나 추출할 수 있도록 설계된 데스크톱 애플리케이션입니다. 최대 2개의 ROI(Region of Interest)를 지정하여 관심 영역의 연속적인 라벨링과 개별 셀 저장을 지원하며, 대용량 이미지에서는 전체 원본을 한 번에 GUI 메모리에 올리지 않고 부분 렌더링 방식으로 동작합니다.

### ✨ 핵심 기능 (Key Features)
#### 1. 전역 그리드 및 탐색
- **전역 좌표계**: ROI가 나뉘어 있어도 번호가 끊기지 않고 이어지는 전역 `Cols`, `Rows` 시스템을 사용합니다.
- **정밀 선택**: 마우스 클릭 또는 `Cell X, Y` 좌표 직접 입력을 통한 단일 셀 선택 기능을 제공합니다.
- **스마트 캔버스**: 마우스 휠을 이용한 확대/축소와 휠 클릭 드래그를 통한 자유로운 패닝을 지원합니다.
- **대용량 이미지 대응**: 현재 보이는 영역만 부분 렌더링하는 방식으로 기존 전체 적재 방식보다 큰 이미지를 더 안정적으로 처리합니다.

#### 2. 영역 지정 (ROI & Crop)
- **ROI 설정**: 두 점 클릭 또는 좌표 수치(L/T/R/B) 입력을 통해 최대 2개의 관심 영역을 설정할 수 있습니다.
- **이미지 크롭**: 드래그가 아닌 두 점 지정 방식을 통해 정확한 영역을 잘라내어 작업할 수 있습니다.

#### 3. 시각화 및 출력
- **커스텀 라벨**: 그리드 라벨의 표시 여부, 크기(50%~300%), 색상을 실시간으로 변경할 수 있습니다.
- **확대 뷰 및 저장**: 선택된 셀은 우측 하단 패널에서 최대 800%까지 확대 확인이 가능하며, 개별 이미지 파일(PNG, JPG, BMP)로 즉시 저장할 수 있습니다.

### 🛠 기술 스택 (Tech Stack)
- **언어**: Python 3.10+
- **GUI 프레임워크**: PySide6 (Qt for Python)
- **이미지 처리**: Pillow
- **배포 빌드**: PyInstaller

### 🚀 시작하기 (Getting Started)
#### 설치 방법
```powershell
# 저장소 클론
git clone [https://github.com/Cobluesky/Image-Grid-Viewer.git](https://github.com/Cobluesky/Image-Grid-Viewer.git)
cd Image-Grid-Viewer

# 가상환경 생성 및 활성화
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 의존성 설치
python -m pip install --upgrade pip
python -m pip install -e .
```

#### 실행 방법
```powershell
python -m app.main
```

#### 실행 파일(EXE) 빌드
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_exe.ps1
```

#### 실행 파일(폴더형) 빌드
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_onedir.ps1
```

### 📂 프로젝트 구조 (Project Structure)
```text
app/
  ├── core/      # 격자 계산 및 좌표 변환 로직
  ├── models/    # AppState 및 이미지 메타데이터 관리
  └── ui/        # 메인 윈도우, 캔버스, 확대 패널 UI
pyproject.toml   # 프로젝트 설정 및 의존성
build_exe.ps1    # 단일 EXE 빌드 스크립트
build_onedir.ps1 # 폴더형 빌드 스크립트
pyinstaller_runtime_env.py # 번들 Qt 경로를 우선 적용하는 런타임 훅
```

### 📄 라이선스 (License)
이 프로젝트는 **MIT License**를 따릅니다.

### 👤 제작자 (Contact)
**신하늘 (Shin Ha-neul)**
- 📧 이메일: [habuhamo900@gmail.com](mailto:habuhamo900@gmail.com)
- 🔗 GitHub: [@Cobluesky](https://github.com/Cobluesky)

---
<p align="center">Please consider starring this repository if you found it useful! / 유용하게 사용하셨다면 ⭐️ Star를 눌러주세요!</p>
