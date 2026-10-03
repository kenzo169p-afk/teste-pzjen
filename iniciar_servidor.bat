@echo off
chcp 65001 > nul
title PJzen - Servidor Handoff Digital
color 0A
cls
echo =======================================================================
echo          PJzen - FORMULÁRIO DIGITAL DE HANDOFF COMERCIAL
echo =======================================================================
echo.
echo  Iniciando o servidor local...
echo  O seu navegador padrao sera aberto automaticamente em:
echo  >> http://localhost:5000
echo.
echo  Para encerrar o servidor a qualquer momento, feche esta janela ou
echo  pressione Ctrl + C.
echo.
echo =======================================================================
echo.

cd /d "%~dp0"

REM Aguarda 2 segundos e abre o navegador
start "" cmd /c "timeout /t 2 /nobreak > nul && start http://localhost:5000"

REM Inicia o servidor Flask com Python
py app.py

pause
