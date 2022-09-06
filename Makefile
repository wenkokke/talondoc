# Minimal makefile for Sphinx documentation
SHELL := bash

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = example/docs
BUILDDIR      = example/docs/_build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

autogen:
	@talondoc autogen \
		--output-dir example/docs/knausj_talon \
		--project "knausj_talon" \
		--package-name user \
		--exclude '**/*.py' \
		--exclude 'modes/wake_up_wav2letter.talon' \
		example/knausj_talon/
	@rm example/docs/knausj_talon/conf.py

serve:
	@(cd $(BUILDDIR)/html && npx browser-sync -ss)

clean:
	@git clean -dfqX
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: autogen help Makefile serve
