%AppData%\talon\Scripts\python.exe -m pip install .[docs]

%AppData%\talon\Scripts\talondoc.exe autogen --output-dir example/docs/knausj_talon --sphinx-root example/docs --project 'knausj_talon' --package-name user --no-generate-conf --exclude '*.py' --exclude 'modes/wake_up_wav2letter.talon' example/knausj_talon/

%AppData%\talon\Scripts\sphinx-build.exe -M "html" "example/docs" "example/docs/_build"
