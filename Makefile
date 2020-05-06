init:
	pip install -r requirements.txt

test:
	py.test tests

clean:
	rm -rf ./build \
	rm -rf ./dist  \
	rm -rf ./tinywin.egg-info

compile:
	python3 setup.py bdist_wheel

install-local:
	python3 -m pip install dist/tinywin*.whl

upload-pypi:
	python3 -m twine upload dist/*

.PHONY: init test