default: build install

build:
	(cd ../..; R CMD build BabelClient)

install: build
	(cd ../..; R CMD install BabelClient)

check:
	(cd ../..; R CMD check --no-latex --no-vignettes --no-codoc --no-examples --no-manual  BabelClient)
