@echo off

IF NOT EXIST ".\env" (
  echo "Install virtualenv"
  %AppData%\talon\.venv\Scripts\python.exe -m pip install virtualenv

  echo "Create virtualenv for TalonDoc"
  %AppData%\talon\.venv\Scripts\python.exe -m venv env
)

echo "Activate virtualenv"
.\env\Scripts\activate

echo "Install TalonDoc"
...\env\Scripts\python.exe -m pip install .[docs]

echo "Generate documentation"
...\env\Scripts\talondoc.exe autogen --output-dir "example/docs/knausj_talon" --sphinx-root "example/docs" --project "knausj_talon" --package-name "user" --no-generate-conf --exclude "tests/**" --exclude "*.py" --exclude "modes/wake_up_wav2letter.talon" "example/knausj_talon/"

echo "Clean up cache"
...\env\Scripts\sphinx-build.exe -M "clean" "example/docs" "example/docs/_build"

echo "Build documentation"
...\env\Scripts\sphinx-build.exe -M "html" "example/docs" "example/docs/_build"
