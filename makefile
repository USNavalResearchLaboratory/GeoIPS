
all:
	@if [[ -v GEOIPS_VIRTUALENV_DIR && -v GEOIPS_EXT_INSTALLDIR ]]; then \
		echo "GEOIPS_VIRTUALENV_DIR ${GEOIPS_VIRTUALENV_DIR} environment variable and ";\
		echo "GEOIPS_EXT_INSTALLDIR ${GEOIPS_EXT_INSTALLDIR} environment variables BOTH exist. Pick one. Not attempting to build geoips and dependencies"; \
		echo "Please source appropriate config_base setup script"; \
	elif [[ -v GEOIPS_VIRTUALENV_DIR && -d `dirname ${GEOIPS_VIRTUALENV_DIR}` ]]; then \
		echo "GEOIPS_VIRTUALENV_DIR " `dirname ${GEOIPS_VIRTUALENV_DIR}` " exists, building and installing geoips bdist_wheel and dependencies using pip virtualenv setup";\
		echo "USING PATHS:";\
		echo "VIRTUALENV:      ${GEOIPS_VIRTUALENV_DIR}";\
		echo "";\
		while [ -z "$$CONTINUE" ]; do \
			read -r -p "Y or y to CONTINUE with GeoIPS build, affecting above paths. If paths are incorrect, source appropriate config_bash setup file. [y/N]: " CONTINUE; \
		done ; \
		if [ $$CONTINUE != "y" ] && [ $$CONTINUE != "Y" ]; then \
			echo "Exiting. Please source appropriate config to set build environment."; exit 1; \
		fi; \
		echo "RUNNING";\
		if [ ! -e ${GEOIPS_VIRTUALENV_DIR} ]; then \
			virtualenv ${GEOIPS_VIRTUALENV_DIR};\
		fi;\
		. ${GEOIPS_VIRTUALENV_DIR}/bin/activate;\
		echo "PYTHONPATH:      ${PYTHONPATH}";\
		echo "PYTHON:          "`which python`;\
		echo "PATH:            ${PATH}";\
		pip install numpy;\
		echo "Installed numpy prior to building geoalgs (for f2py)";\
		make -f makefile_geoips; \
		cp -p dist/geoips*${GEOIPS_VERS}*.whl `dirname ${GEOIPS_VIRTUALENV_DIR}`;\
		cd `dirname ${GEOIPS_VIRTUALENV_DIR}`;\
		make;\
		make install;\
	elif [[ -v GEOIPS_EXT_INSTALLDIR && -d `dirname ${GEOIPS_EXT_INSTALLDIR}` ]]; then \
		echo "GEOIPS_EXT_INSTALLLDIR " `dirname ${GEOIPS_EXT_INSTALLDIR}` " exists, building and installing geoips and dependencies from source";\
        echo "GEOIPS_EXT_INSTALLDIR: ${GEOIPS_EXT_INSTALLDIR}";\
		echo "";\
		while [ -z "$$CONTINUE" ]; do \
			read -r -p "Y or y to CONTINUE with GeoIPS build, affecting above paths. If paths are incorrect, source appropriate config_bash setup file. [y/N]: " CONTINUE; \
		done ; \
		if [ $$CONTINUE != "y" ] && [ $$CONTINUE != "Y" ]; then \
			echo "Exiting. Please source appropriate config to set build environment."; exit 1; \
		fi; \
		echo "RUNNING"; \
		cd `dirname ${GEOIPS_EXT_INSTALLDIR}`; \
		make; \
		make install; \
		if [[ -v STANDALONE_GEOIPS ]]; then \
			cd "${STANDALONE_GEOIPS}" ; \
		else \
			cd ${GEOIPS}; \
		fi; \
		make -f makefile_geoips; \
	elif [[ -v GEOIPS_VIRTUALENV_DIR ]]; then \
		echo "GEOIPS_VIRTUALENV_DIR " `dirname ${GEOIPS_VIRTUALENV_DIR}` " directory DOES NOT EXIST, not attempting to build geoips and dependencies"; \
	elif [[ -v GEOIPS_EXT_INSTALLDIR ]]; then \
		echo "GEOIPS_EXT_INSTALLDIR " `dirname ${GEOIPS_EXT_INSTALLDIR}` " directory DOES NOT EXIST, not attempting to build geoips and dependencies"; \
	else \
		echo "GEOIPS_VIRTUALENV_DIR and GEOIPS_EXT_INSTALLDIR DO NOT EXIST, not attempting to build geoips and dependencies."; \
		echo "Source appropriate config_bash setup file to set environment"; \
	fi
