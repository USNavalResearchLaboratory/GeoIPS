
all:
	@if [ -e ../geoips_dependencies ]; then \
		echo "geoips_dependencies exists, installing building geoips bdist_wheel"; \
	else \
		echo "geoips_dependencies DOES NOT EXIST, not attempting to build geoips bdist_wheel"; \
		exit 1; \
	fi
	@echo "USING PATHS:"
	@echo "GEOIPS:          ${GEOIPS}"
	@echo "EXTERNAL_GEOIPS: ${EXTERNAL_GEOIPS}"
	@echo "VIRTUALENV:      ../geoips_dependencies/packages"
	@echo ""
	@while [ -z "$$CONTINUE" ]; do \
        read -r -p "Y or y to CONTINUE with GeoIPS build, affecting above paths. [y/N]: " CONTINUE; \
    done ; \
    if [ $$CONTINUE != "y" ] && [ $$CONTINUE != "Y" ]; then \
		echo "Exiting. Please source appropriate config to set build environment."; exit 1; \
	fi
	#sudo pip install virtualenv;
	@echo "RUNNING";\
	virtualenv ../geoips_dependencies/packages;\
	. ../geoips_dependencies/packages/bin/activate;\
	echo "PYTHONPATH:      ${PYTHONPATH}";\
	echo "PYTHON:          "`which python`;\
	echo "PATH:            ${PATH}";\
	pip install numpy;\
	python remove_links.py all;\
	python create_links.py;\
	python setup.py bdist_wheel
