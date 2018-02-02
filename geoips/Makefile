SOURCEDIR = $(shell pwd)
TARGETS = geoalgs

GOALS = $(filter-out ${TARGETS}, ${MAKECMDGOALS})

.PHONY: all
all: ${TARGETS}

.PHONY: clean
clean: ${TARGETS}

.PHONY: ${TARGETS}
${TARGETS}:
	make -C $@ -f ${SOURCEDIR}/$@/Makefile ${GOALS}

