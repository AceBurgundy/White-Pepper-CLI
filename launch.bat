@echo off
echo Starting local documentation server at http://localhost:9000 ...
start http://localhost:9000
python -m http.server 9000
