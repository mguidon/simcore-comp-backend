PY_FILES = $(strip $(shell find modules -iname '*.py'))

pylint:
	# See exit codes and command line https://pylint.readthedocs.io/en/latest/user_guide/run.html#exit-codes
	/bin/bash -c "pylint --rcfile=.pylintrc --disable=import-error --disable=fixme --disable=C $(PY_FILES)"
