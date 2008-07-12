#MKHTML=mkdoc
#MKHTMLOPTS=--doctype book --param toc.section.depth=2  --target html --stylesheet single-file
#SRC=.

#TXTFILES:= $(wildcard *.txt)
#TARGET := $(TXTFILES:.txt=.html)

all: apydoc

#%.html: %.txt
#        ${MKHTML} ${MKHTMLOPTS} $<

apydoc:
	epydoc --html -v --graph all --no-private --exclude="__pkginfo__" --exclude="setup" -n "Yams Module" ..

clean:
	rm -f *.html
	rm -rf html
