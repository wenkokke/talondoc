@echo off

echo "Install TalonDoc"
%AppData%\talon\.venv\Scripts\python.exe -m pip install .[docs]

echo "Generate documentation"
%AppData%\talon\.venv\Scripts\talondoc.exe autogen --output-dir "example/docs/knausj_talon" --sphinx-root "example/docs" --project "knausj_talon" --package-name "user" --no-generate-conf --exclude "tests/**" --exclude "*.py" --exclude "modes/wake_up_wav2letter.talon" "example/knausj_talon/"

echo "Clean up cache"
%AppData%\talon\.venv\Scripts\sphinx-build.exe -M "clean" "example/docs" "example/docs/_build"

echo "Build documentation"
%AppData%\talon\.venv\Scripts\sphinx-build.exe -M "html" "example/docs" "example/docs/_build"
