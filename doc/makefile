all: apydoc

apydoc:
	epydoc --html -o apidoc -v --graph all --no-private --exclude="__pkginfo__" --exclude="setup" -n "Yams Module" ..

clean:
	rm -f *.html
	rm -rf apidoc
