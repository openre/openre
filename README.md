# OpenRE

Библиотека для моделирования распределенной нейронной сети.
Моделирование происходит на GPU или CPU устройствах.

## Install

Пример установки для Ubuntu.

Перед установкой было проделано:
sudo apt-get install build-essential python-dev

Желательно поставить virtualenvwrapper - иструкция написана исходя из предположения что он стоит.

Для установки pyopencl нужно сначала скачать заголовочные файлы и любой ICD Loader, а так же опционально реализацию (ICD implementation).
Согласно этой странице http://wiki.tiker.net/OpenCLHowTo#Debian устанавливаем:
ICD Loader:
sudo apt-get install amd-libopencl1

Далее я установил AMD ICD loader и CPU ICD согдласно инструкции тут (Installing the AMD ICD loader and CPU ICD (from the "APP SDK")):
http://wiki.tiker.net/OpenCLHowTo#Installing_the_AMD_ICD_loader_and_CPU_ICD_.28from_the_.22APP_SDK.22.29
Скачиваем архив для системы, распаковываем и запускаем:
sudo ./AMD-APP-SDK-VERSION-GA-linux64.sh
После установки я дополнительно сделал (если pip install -r requirements.txt отрабатывает без ошибки, то этот шаг не нужен):
cd /usr/lib
sudo ln -s ../../opt/AMDAPPSDK-3.0/lib/x86_64/libOpenCL.so
В этом случае ошибки (/usr/bin/ld: cannot find -lOpenCL) при компиляции pyopencl (это будет ниже) не возникает, но очевидно это не очень правильно.

Далее сама установка
git clone https://github.com/openre/openre.git
cd openre
mkvirtualenv openre
pip install -r requirements.txt # без этого setup.py не работает
./setup.py install

