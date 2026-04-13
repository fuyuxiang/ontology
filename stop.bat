@echo off
echo Stopping services...
taskkill /FI "WINDOWTITLE eq Ontology-Backend*" /F 2>nul
taskkill /FI "WINDOWTITLE eq Ontology-Frontend*" /F 2>nul
echo Done.
