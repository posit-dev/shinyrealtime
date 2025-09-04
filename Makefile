.PHONY: all clean build install test js

all: build

clean:
	rm -rf pkg-r/inst/www/*.js
	rm -rf pkg-r/inst/www/*.css
	rm -rf pkg-py/src/shinyrealtime/www/*.js
	rm -rf pkg-py/src/shinyrealtime/www/*.css

www/app.css www/app.js &: src/*
	node build.js

js: www/app.css www/app.js

build-r: js
	mkdir -p pkg-r/inst/www
	cp www/app.js pkg-r/inst/www/
	cp www/app.css pkg-r/inst/www/
	cd pkg-r && R CMD build .

build-py: js
	uv sync
	mkdir -p pkg-py/src/shinyrealtime/www
	cp www/app.js pkg-py/src/shinyrealtime/www/
	cp www/app.css pkg-py/src/shinyrealtime/www/

build: build-r build-py

install-r: build-r
	R CMD INSTALL pkg-r

install-py: build-py
	uv pip install -e .

install: install-r install-py

test-r:
	cd pkg-r && R CMD check --no-manual --no-build-vignettes .

test-py:
	uv run pytest pkg-py/tests/

test: test-r test-py

demo-r:
	R --quiet -e "shiny::runApp(launch.browser=TRUE)"

demo-py:
	uv run app.py