.PHONY: default pdf clean
default:
	doxygen doxyfile
	# Load static setup from legato
ifdef LEGATO_ROOT
	cp $(LEGATO_ROOT)/framework/doc/static/* html
else
	cp ../../legato/framework/doc/static/* html
endif
	# for scrollbar
	sed -i -E "s/overflow: *hidden/overflow: auto/g" html/legato.css
pdf: default
	make -C latex
	ln -s $(CURDIR)/latex/refman.pdf letp.pdf
letp.legato.io: default
	rm ../../../build/doc/letp/html
	ln -s $(CURDIR)/html ../../../build/doc/letp/html
	OUTPUT_DIR=$(CURDIR)/legato_io_style/ \
	make -C ../../../docManagement letp
clean:
	rm -rf html
	rm -rf latex
	rm -f ../../../build/doc/letp/html
	rm -rf _sphinx
	rm letp.pdf

# Minimal makefile for Sphinx documentation
#
SPHINXOPTS    =
SPHINXBUILD   = LD_LIBRARY_PATH=$$LEGATO_ROOT/build/localhost/framework/lib/:$$LD_LIBRARY_PATH python3 -msphinx
SPHINXPROJ    = LeTP
SOURCEDIR     = .
BUILDDIR      = _sphinx

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
