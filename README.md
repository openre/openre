# OpenRE

Библиотека для моделирования распределенной нейронной сети.
Моделирование происходит на GPU или CPU устройствах.

## Install

### Стабильный релиз
```bash
pip install openre
```

### Пример установки из репозитория для Ubuntu

Перед установкой было проделано:
```bash
sudo apt-get install build-essential python-dev
```

Желательно поставить virtualenvwrapper - иструкция написана исходя из предположения что он стоит.

Для установки pyopencl нужно сначала скачать заголовочные файлы и любой ICD Loader, а так же опционально реализацию (ICD implementation).

Для примера я установил AMD ICD loader и CPU ICD согдласно инструкции [тут](http://wiki.tiker.net/OpenCLHowTo#Installing_the_AMD_ICD_loader_and_CPU_ICD_.28from_the_.22APP_SDK.22.29) (Installing the AMD ICD loader and CPU ICD (from the "APP SDK")):
Скачиваем архив для системы, распаковываем и запускаем:
```bash
sudo ./AMD-APP-SDK-VERSION-GA-linux64.sh
```

Далее сама установка
```bash
git clone https://github.com/openre/openre.git
cd openre
mkvirtualenv openre
export CPLUS_INCLUDE_PATH=$CPLUS_INCLUDE_PATH:/opt/AMDAPPSDK-3.0/include && export LIBRARY_PATH=$LIBRARY_PATH:/opt/AMDAPPSDK-3.0/lib/x86_64 && ./setup.py install
```
