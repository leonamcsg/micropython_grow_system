# timer_module - testando e ultilizado com esp8266 - autor: leonam C S Gomes)
# BASEADO EM...
# Module to read adc soil moisture and save on memory
# https://github.com/KIT-HYD/ESP32-Soil-Moisture/blob/main/src/sm.py
#               MIT License
#    Copyright (c) 2021 Hydrology @KIT
#    https://opensource.org/license/mit

import json
from machine import ADC
from collections import deque

def config(new_config = None):
    """
    Read and write to the config.json file
    """
    conf = None
    if new_config is None:
        try:
            print('tentando ler valores de calibragem')
            with open('/config/sm_config.json', 'r') as f:
                conf = json.load(f)
                print('valores de calibragem carregados com sucesso!')
        except (OSError, ValueError) as exc:
            print("erro ao carregar sm_config:", exc)
    else:
        with open('/config/sm_config.json', 'w') as f:
            json.dump(new_config, f)
            return new_config
    return conf

def save_internal(values: tuple, maxlen=20):
    print('salvando valores de leitura de umidade')
    # verifica arquivo
    l = read_internal()
    
    # cria o deque
    manager = deque(l, int(maxlen))
    manager.append({'raw': values[1], 'moisture': values[0], 'date': values[2]})

    # salva
    with open('/config/readings.json', 'w') as f:
        json.dump(list(manager), f)
        print('novos registros de leitura salvos!')

def read_internal():
    # verifica arquivo
    try:
        print('tentando acessar registros de leituras')
        with open('/config/readings.json', 'r') as f:
            l = json.load(f)
            print('registros carregados!')
    except (OSError, ValueError) as exc:
        print('erro ao carregar readings.json', exc)
        print('iniciando lista de leituras do sensor vazia...')
        l = []
    
    return l

def read(adc = None, calibrationAir = None, calibrationWater = None, cycle=5):
    """
    Read a Capacitive soil moisture sensor with analog output.
    """
    # Cria adc se não é passado
    if adc is None:
        adc = 0
    if isinstance(adc, int):
        adc = ADC(adc)
    
    # verifica se os valores de calibragem foram passados
    if calibrationAir is None or calibrationWater is None:
        print('ultilizando valores padrão...')
        conf = config({'calibrationAir': 750, 'calibrationWater': 300})
        if calibrationAir is None:
            calibrationAir = conf['calibrationAir']
        if calibrationWater is None:
            calibrationWater = conf['calibrationWater']
    
    # realiza leitura
    raw = 0
    for _ in range(cycle):
        raw += adc.read()
    raw /= cycle

    # mapeia valores # vai de 0 a 1024
    if raw < calibrationWater:
        sm = 100
    elif raw > calibrationAir:
        sm = 0
    else:
        sm = (1 - ((raw - calibrationWater) / (calibrationAir - calibrationWater))) * 100

    return sm, raw