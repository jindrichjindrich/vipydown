cd %~dps0
set HTTP_PORT=8000
set MKDOCS_PORT=8001
set action=%1
if "%action%" == "" goto help
goto %action%

:mkdocs-server
start mkdocs server
goto end

:mkdocs-build
:: create site/ subfolder with html docs
mkdocs build
goto end

:make-link
pushd docs
mklink README.md %~dps0\README.md
popd
goto end

:python-server
pushd site
start http://localhost:%HTTP_PORT%
start python -m http.server %HTTP_PORT%
popd
goto end

:help
echo Usage: run ACTION
echo ACTION: 
echo make-link     ... link README.md to docs/README.md (for mkdocs)
echo mkdocs-server ... start mkdocs server serving docs/README.md
echo mkdocs-build  ... make html docs in site/ subfolder
echo python-server ... start python http server
goto end

:end