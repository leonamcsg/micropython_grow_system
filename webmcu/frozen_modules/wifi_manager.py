import network
import time
import json

# Função para conectar uma rede wifi especifica 
def wifi_connect(sta_if, sta_ssid, sta_key, timeout):
    if sta_ssid:
        # Tenta conectar
        if not sta_if.isconnected():
            print('starting new connection to WIFI: \'' + sta_ssid + '\', PASSWORD: ' + '\'' + sta_key + '\'')
        else :
            print('already connected to WIFI: \'' + sta_if.config('ssid') + '\'')
            print('starting new connection to WIFI: \'' + sta_ssid + '\', PASSWORD: ' + '\'' + sta_key + '\'')
        sta_if.connect(sta_ssid, sta_key)
        # Espera até conectado
        t = time.ticks_ms()
        while not sta_if.isconnected():
            if time.ticks_diff(time.ticks_ms(), t) > timeout:
                sta_if.disconnect()
                print("conection timeout. Could not connect.")
                return sta_if.status()
        print('connection successful!')
        print('network config:', sta_if.ifconfig())
        print('hostname: ' + '\'' + network.hostname() + '.local\'\n')
    else:
        print('ERRO: SSID vazio!')
        return 'SSID vazio'
    return sta_if.status()

# Função para criar um ponto de acesso wifi
def ap_create(ap_ssid, ap_key):
    ap_if = network.WLAN(network.AP_IF)
    if ap_if.active():
        print('modifying Access Point: ' + '\'' + ap_if.config('ssid') + '\'')
    else:
        print('creating Access Point: ')
    ap_if.active(True)
    ap_if.config(ssid=ap_ssid, key=ap_key)
    print('SSID: ' + '\'' + ap_if.config('ssid') + '\'' + ', PASSWORD: ' + '\'' + ap_key + '\'')
    print('network config:', ap_if.ifconfig())
    print('hostname: ' + '\'' + network.hostname() + '.local\'\n')

# Carrega credenciais wifi do arquivo json
def load_wifi_config():
    try:
        with open('/config/wifi_config.json', 'r') as f:
            config = json.load(f)
            return config['ssid'], config['password']
    except (OSError, ValueError):
        # Trate o caso em que o arquivo não existe ou está corrompido
        return None, None

# Salva credenciais wifi no arquivo json
def save_wifi_config(ssid, password):
    config = {
        'ssid': ssid,
        'password': password
    }
    with open('/config/wifi_config.json', 'w') as f:
        json.dump(config, f)
        