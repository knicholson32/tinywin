init:
	pip install -r ./requirements.txt

init-dev:
	pip install -r ./requirements/dev.txt

test:
	py.test tests

v-build:
	bumpversion build --allow-dirty; cat VERSION

v-patch:
	bumpversion patch --allow-dirty; cat VERSION

v-minor:
	bumpversion minor --allow-dirty; cat VERSION

v-major:
	bumpversion major --allow-dirty; cat VERSION

v-release:
	bumpversion --tag release --allow-dirty; cat VERSION

clean:
	rm -rf ./build
	rm -rf ./dist
	rm -rf ./tinywin.egg-info

compile:
	python3 setup.py bdist_wheel

install-local:
	make clean
	make compile
	python3 -m pip install dist/tinywin*.whl

upload-pypi:
	make clean
	bump2version patch --verbose --allow-dirty
	make compile
	python3 -m twine upload dist/*

.PHONY: init test