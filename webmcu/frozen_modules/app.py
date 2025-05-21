import network
import socket
import errno
import gc

# Frozen modules in firmware micropython/ports/esp8266/modules/...
import request_parser
import wifi_manager
import timers_module
import utils_module

# Constantes de chaveamento de pedido de endereço
STATIC_HTML_REQUEST = const(0)
INDEX_REQUEST = const(1)
WIFI_MANAGER_REQUEST = const(2)
LIGHT_SETTINGS_REQUEST = const(3)
WATER_SETTINGS_REQUEST = const(4)

# Parametros para network
sta_ssid_default = ''
sta_password_default = ''
ap_ssid = 'nodecmu'
ap_password = 'admin123'
conection_timeout = 15000 # 15s

# Função com loop principal
# ------------------------
def execute():
    gc.enable() # habilita 'garbage collector'
    gc.collect() # Desfragmenta memoria

    timers_module.init(False)
    utils_module.tm_paused = False

    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)

    # Carregando credenciais do armazenadas em arquivo
    sta_ssid_default, sta_password_default = wifi_manager.load_wifi_config() # retorna None caso vazio ou corrompido

    # Tenta conectar Wifi
    if not sta_ssid_default == None :
        wifi_status = wifi_manager.wifi_connect(sta_if, sta_ssid_default, sta_password_default, conection_timeout)
    else:
        wifi_status = sta_if.status()

    print('Status:', wifi_status, sta_if.isconnected())
    print('SSID: \'' + sta_if.config('ssid') + '\'')

    # Iniciar access point
    wifi_manager.ap_create(ap_ssid, ap_password)

    # Iniciar o servidor HTTP
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(5) # escuta até 5 clientes
    print('server started...\nlistening on:', addr)

    gc.collect()

    # Loop principal
    while True:
        print('Memoria livre:', gc.mem_free())
        print('Memoria alocada:', gc.mem_alloc())
        # Aceita conexao com cliente
        conn_closed = False
        raw_request = ''
        while True:
            gc.collect()
            try:
                print('aguardando pedido de conexao...')
                cl, addr = s.accept()
                print('Client connected from', addr)
                cl.settimeout(10) # Tempo em segundos
                raw_request = cl.recv(1024) # Aguarda pedido
                request = str(raw_request) # Pedido aceito
                cl.settimeout(20) # Reinicia timer
                break
            except Exception as exc:
                if exc.errno == errno.ETIMEDOUT:
                    print('reiniciando timer de conexao')
                    cl.close()
                else:
                    raise exc  
        rqt_parser = request_parser.RequestParser(raw_request)
        raw_request = None # limpa pedido cru
        print('method:', rqt_parser.method)
        url = rqt_parser.url
        print('url:', url)
        data = rqt_parser.data()
        print('data:', data)
        rqt_parser = None # limpa pedido

        html_script = '' # tag para injetar javascript
        html_request = STATIC_HTML_REQUEST # Pedido html

        gc.collect() # limpa e desfragmenta memória

        # Responder com o conteúdo do arquivo HTML
        if url == '/':
            html_request = INDEX_REQUEST
        elif url == '/wifi_manager':
            html_request = WIFI_MANAGER_REQUEST
        elif url == '/light_configuration':
            html_request = LIGHT_SETTINGS_REQUEST
        elif url == '/irrigation_configuration':
            html_request = WATER_SETTINGS_REQUEST
        elif url == '/static/style.css': # Envia style.css
            response = 'HTTP/1.1 200 OK\nContent-Type: text/css\n\n' + utils_module.read_file('static/style.css', 'r')
        elif url == '/src/light_conf.js':
            response = 'HTTP/1.1 200 OK\nContent-Type: text/javascript\n\n' + utils_module.read_file('/src/light_conf.js', 'r')
        elif url == '/src/irrigation_conf.js':
            response = 'HTTP/1.1 200 OK\nContent-Type: text/javascript\n\n' + utils_module.read_file('/src/irrigation_conf.js', 'r')      
        elif url == '/src/index.js':
            response = 'HTTP/1.1 200 OK\nContent-Type: text/javascript\n\n' + utils_module.read_file('/src/index.js', 'r')
        elif url == '/src/wifi_manager.js':
            response = 'HTTP/1.1 200 OK\nContent-Type: text/javascript\n\n' + utils_module.read_file('/src/wifi_manager.js', 'r')
        elif url == '/img/leaf.png': # Envia icone
            response = 'HTTP/1.1 200 OK\nContent-Type: image/png\n\n'
            cl.send(response)
            response = utils_module.read_file('img/leaf.png', 'rb') # rb -> 'read binary'
        elif url == '/img/hamburger_icon.svg': # Envia hamburguer 
            response = 'HTTP/1.1 200 OK\nContent-Type: image/svg+xml\n\n'
            cl.send(response)
            response = utils_module.read_file('img/hamburger_icon.svg', 'r')
        elif url == '/connect_wifi':
            sta_ssid = data['wifi_name']
            print(sta_ssid)
            sta_password = data['wifi_password']
            print(sta_password)
            # Tenta iniciar conexão
            sta_if.active(True)
            wifi_manager.wifi_connect(sta_if, sta_ssid, sta_password, conection_timeout)
            if sta_if.isconnected():
                html_request = INDEX_REQUEST
                wifi_manager.save_wifi_config(sta_ssid, sta_password)
                html_script = '<script>alert("Sucesso ao conectar Wifi!"); window.location.replace("/");</script>'
            else :
                html_request = WIFI_MANAGER_REQUEST
                html_script = 'alert("Falha ao conectar Wifi!"); window.location.replace("/wifi_manager");'
        elif url == '/disconnect_wifi':
            if sta_if.isconnected():
                print('desconectando wifi...')
                cl.close()
                conn_closed = True
                sta_if.disconnect()
                sta_if.active(False)
            else :
                conn_closed = False
                html_request = WIFI_MANAGER_REQUEST
        elif url == '/update_light':
            print('alarme de luz a ser criado!')
            if data['mode'] == 'vege' :
                id = 3
            elif data['mode'] == 'flor':
                id = 4
            elif data['mode'] == 'germ':
                id = 5
            timers_module.alarmes[id]['hora_inicio'] = data['start'][0:2]
            timers_module.alarmes[id]['minuto_inicio'] = data['start'][3:5]
            timers_module.alarmes[id]['hora_fim'] = data['end'][0:2]
            timers_module.alarmes[id]['minuto_fim'] = data['end'][3:5]
            timers_module.salvar_alarmes()
            timers_module.alarms_changed = True
            print('Modificacao:', timers_module.alarmes[id])
            response = 'HTTP/1.1 202 Accepted\nContent-Type: application/json\n\n'
            response += '{\n"message": "Luz atualizada!", "modo": "'+ timers_module.alarmes[id]['modo'] +'"\n}\n'
        elif '/create_irrigation_timer' in url: # trocar para /update_water_timer
            print('alarme de irrigacao a ser criado!')
            id = int(ord(url[-1]) - ord('0'))
            timers_module.alarmes[id]['dias_intervalo'] = data['interval_days']
            timers_module.alarmes[id]['hora'] = data['time'][0:2]
            timers_module.alarmes[id]['minuto'] = data['time'][3:5]
            timers_module.salvar_alarmes()
            timers_module.alarms_changed = True
            print('Modificacao:', timers_module.alarmes[id])
            response = 'HTTP/1.1 202 Accepted\nContent-Type: application/json\n\n'
            response += '{\n"message": "Timer' + str(id) + ' atualizado!", "timer": "timer' + str(id) + '"\n}\n'
        elif url == '/get_light_info':
            if data['mode'] == 'vege' :
                id = 3
            elif data['mode'] == 'flor':
                id = 4
            elif data['mode'] == 'germ':
                id = 5
            response = 'HTTP/1.1 202 Accepted\nContent-Type: application/json\n\n'
            response += str('{\n"message": "Modo de iluminação requisitado: ' + timers_module.alarmes[id]['modo'] + 
            '", "start": "' + str(timers_module.alarmes[id]['hora_inicio']) + ':' + str(timers_module.alarmes[id]['minuto_inicio']) + 
            '", "stop": "' + str(timers_module.alarmes[id]['hora_fim']) + ':' + str(timers_module.alarmes[id]['minuto_fim']) + '"\n}\n')
        elif url == '/get_water_info':
            id = data['timer']
            id = int(ord(id) - ord('0'))
            response = 'HTTP/1.1 202 Accepted\nContent-Type: application/json\n\n'
            response += ('{\n"message": "Timer requisitado: timer' + str(data['timer']) + '", "start": "' +
            str(timers_module.alarmes[id]['hora']) + ':' + str(timers_module.alarmes[id]['minuto']) + 
            '", "interval_days": "' + str(timers_module.alarmes[id]['dias_intervalo']) + '"\n}\n')    
        elif url == '/active_timer':
            id = data['timer']
            id = int(ord(id) - ord('0'))
            timers_module.active_water_timers.add(id)
            timers_module.salvar_alarmes()
            timers_module.alarms_changed = True
            response = 'HTTP/1.1 202 Accepted\nContent-Type: application/json\n\n'
            response += ('{\n"message": "Timers ' + str(timers_module.active_water_timers)
            + ' ativos!", "timers": "'+ str(timers_module.active_water_timers) + '"\n}\n')
        elif url == '/turn_off_timer': # trocar para /deactive_timer
            id = data['timer']
            id = int(ord(id) - ord('0'))
            try:
                timers_module.active_water_timers.remove(id)
                timers_module.salvar_alarmes()
                timers_module.alarms_changed = True
            except Exception as exc:
                print(exc)
            response = 'HTTP/1.1 202 Accepted\nContent-Type: application/json\n\n'
            response += ('{\n"message": "Timers ' + str(timers_module.active_water_timers)
            + ' ativos!", "timers": "'+ str(timers_module.active_water_timers) + '"\n}\n')
        elif url == '/active_light':
            if data['mode'] == 'vege' :
                light_mode = 'Vegetação'
            elif data['mode'] == 'flor':
                light_mode = 'Floração'
            elif data['mode'] == 'germ':
                light_mode = 'Germinação'
            timers_module.active_light_mode = light_mode
            timers_module.salvar_alarmes()
            timers_module.alarms_changed = True
            light_mode = None
            response = 'HTTP/1.1 202 Accepted\nContent-Type: application/json\n\n'
            response += ('{\n"message": "Modo ' + timers_module.active_light_mode + ' ativado!",'
            + ' "modo": "' + timers_module.active_light_mode + '"\n}\n')
        elif url == '/pause_tm':
            timers_module.deinit(True)
            utils_module.tm_paused = True
            response = 'HTTP/1.1 202 Accepted\nContent-Type: application/json\n\n'
            response += '{\n"message": "Timers pausados!"\n}\n'
        elif url == '/turn_on_light':
            timers_module.controlar_pino(timers_module.l_pin, 1)
            response = 'HTTP/1.1 202 Accepted\nContent-Type: application/json\n\n'
            response += '{\n"message": "Luz ligada!"\n}\n'
        elif url == '/turn_off_light':
            timers_module.controlar_pino(timers_module.l_pin, 0)
            response = 'HTTP/1.1 202 Accepted\nContent-Type: application/json\n\n'
            response += '{\n"message": "Luz desligada!"\n}\n'
        elif url == '/turn_on_water':
            duracao_ms = 3000 # REFAT: Alterar para valor armazenado em timers_module.alarmes[n]['duracao_ms']
            timers_module.water_one_shot(duracao_ms) # liga irrigação por duracao_ms milisegundos
            response = 'HTTP/1.1 202 Accepted\nContent-Type: application/json\n\n'
            response += '{\n"message": "Irrigação iniciada com duração de '+ str(duracao_ms/1000) +' segundos!"\n}\n'
        elif url == '/resume_tm':
            response = 'HTTP/1.1 202 Accepted\nContent-Type: application/json\n\n'
            if utils_module.tm_paused:
                timers_module.init(True)
                utils_module.tm_paused = False
                response += '{\n"message": "Timers retomados!"\n}\n'
            else:
                response += '{\n"message": "Timers já estão ligados!"\n}\n'
        elif url == '/humidity_sensor':
            response = 'HTTP/1.1 200 OK\nContent-Type: text/html\n\n' + utils_module.read_file('static/humidity_sensor.html', 'r')
        elif url == '/src/plotlib.js' :
            response = 'HTTP/1.1 200 OK\nContent-Type: text/javascript\n\n' + utils_module.read_file('/src/plotlib.js', 'r')
        elif url == '/src/humidity_sensor.js' :
            response = 'HTTP/1.1 200 OK\nContent-Type: text/javascript\n\n' + utils_module.read_file('/src/humidity_sensor.js', 'r')
        elif url == '/config/readings.json' :
            response = 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n' + utils_module.read_file('/config/readings.json', 'r')
        else:
            response = 'HTTP/1.1 404 Not Found\n\n'
            
        gc.collect() # Limpa e desfragmenta memória

        # Caso seja um pedido para o html analisa variáveis
        wifi_isconnected = None
        wifi_name = None
        if html_request == WIFI_MANAGER_REQUEST:
            wifi_isconnected = sta_if.isconnected()
            wifi_name = sta_if.config('ssid')

        if not html_request == STATIC_HTML_REQUEST:
            response = utils_module.html_response(html_request, wifi_isconnected, wifi_name, html_script)
        
        if not conn_closed :
            try:
                cl.sendall(response)
            except OSError as exc:
                if exc.errno == errno.ECONNRESET:
                    print('ERRO: pedido de reinicio de comunicacao')
                else :
                    raise exc
                print('nao envia resposta')
            cl.close()
        
        # limpando lixo e desfragmentando
        html_request = None
        data = None
        response = None
        html_script = None
        gc.collect()
