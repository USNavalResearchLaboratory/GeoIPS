
all:
	@if [ ${GEOIPS_VIRTUALENV_DIR} ] && [ ${GEOIPS_EXT_INSTALLDIR} ]; then \
		echo "GEOIPS_VIRTUALENV_DIR ${GEOIPS_VIRTUALENV_DIR} environment variable and "; \
		echo "GEOIPS_EXT_INSTALLDIR ${GEOIPS_EXT_INSTALLDIR} environment variables BOTH exist. Pick one. Not attempting to build geoips and dependencies"; \
		echo "Please source appropriate config_base setup script"; \
	elif [ ${GEOIPS_VIRTUALENV_DIR} ] && [ -d `dirname ${GEOIPS_VIRTUALENV_DIR}` ]; then \
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
		cd `dirname ${GEOIPS_VIRTUALENV_DIR}`; \
		make;\
		make install;\
	elif [ ${GEOIPS_EXT_INSTALLDIR} ] && [ -d `dirname ${GEOIPS_EXT_INSTALLDIR}` ]; then \
		echo "GEOIPS_EXT_INSTALLLDIR " `dirname ${GEOIPS_EXT_INSTALLDIR}` " exists, building and installing geoips and dependencies from source";\
        echo "GEOIPS_EXT_INSTALLDIR: ${GEOIPS_EXT_INSTALLDIR}";\
		echo "";\
		while [ -z "$$CONTINUE2" ]; do \
			read -r -p "Y or y to CONTINUE with GeoIPS build, affecting above paths. If paths are incorrect, source appropriate config_bash setup file. [y/N]: " CONTINUE2; \
		done ; \
		if [ $$CONTINUE2 != "y" ] && [ $$CONTINUE2 != "Y" ]; then \
			echo "Exiting. Please source appropriate config to set build environment."; exit 1; \
		fi; \
		echo "RUNNING"; \
		cd `dirname ${GEOIPS_EXT_INSTALLDIR}`; \
		make; \
		grep HAVE_ISNAN basemap*/geos*/include/geos/platform.h; \
		echo "NOTE some builds fail to set HAVE_ISNAN in geos/platform.h - if it is not set above,"; \
		echo "Please manually change line 24 of "; \
		echo `dirname ${GEOIPS_EXT_INSTALLDIR}`"/basemap*/geos*/include/geos/platform.h"; \
		echo "#define HAVE_ISNAN 1"; \
		echo "Then continue with make install"; \
		while [ -z "$$CONTINUE3" ]; do \
			read -r -p "Y or y to CONTINUE with make install? [y/N]: " CONTINUE3; \
		done ; \
		if [ $$CONTINUE3 != "y" ] && [ $$CONTINUE3 != "Y" ]; then \
			echo "Exiting. Please ensure build environment is correct."; exit 1; \
		fi; \
		make install; \
		if [ ${STANDALONE_GEOIPS} ]; then \
			cd "${STANDALONE_GEOIPS}" ; \
		else \
			cd ${GEOIPS}; \
		fi; \
		make -f makefile_geoips; \
	elif [ ${GEOIPS_VIRTUALENV_DIR} ]; then \
		echo "GEOIPS_VIRTUALENV_DIR " `dirname ${GEOIPS_VIRTUALENV_DIR}` " directory DOES NOT EXIST, not attempting to build geoips and dependencies"; \
	elif [ ${GEOIPS_EXT_INSTALLDIR} ]; then \
		echo "GEOIPS_EXT_INSTALLDIR " `dirname ${GEOIPS_EXT_INSTALLDIR}` " directory DOES NOT EXIST, not attempting to build geoips and dependencies"; \
	else \
		echo "GEOIPS_VIRTUALENV_DIR and GEOIPS_EXT_INSTALLDIR DO NOT EXIST, not attempting to build geoips and dependencies."; \
		echo "Source appropriate config_bash setup file to set environment"; \
		echo "GEOIPS_VIRTUALENV_DIR ${GEOIPS_VIRTUALENV_DIR}"; \
	fi
