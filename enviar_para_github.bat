@echo off
chcp 65001 >nul
echo ========================================================
echo  PJzen - Enviando Sistema Completo para o GitHub
echo ========================================================
echo.
echo Enviando arquivos para o repositorio:
echo https://github.com/kenzo169p-afk/teste-pzjen
echo.
git push origin main
echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================================
    echo  SUCESSO! O codigo do sistema esta publicado no GitHub!
    echo ========================================================
) else (
    echo ========================================================
    echo  AVISO: Faca o login no GitHub se uma janela se abrir.
    echo ========================================================
)
echo.
pause
