[aliases]
test=pytest

[tool:pytest]
;add --roodir here will become effective, but when run pytest command
;the printed message of rootdir is only can be changed by command
;line, so never mind!
addopts = --rootdir=${pwd}/tests --cov-report=html:${pwd}/htmlcov --cov-branch --cov=${pwd}/pytest_apistellar/ -vv --disable-warnings
syspath =
    ${pwd}/tests
item =
    factories.data["a"]=11
usefixtures =
    mock