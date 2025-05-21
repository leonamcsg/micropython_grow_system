import timers_module
import rtc_module
import gc

INDEX_REQUEST = const(1)
WIFI_MANAGER_REQUEST = const(2)
LIGHT_SETTINGS_REQUEST = const(3)
WATER_SETTINGS_REQUEST = const(4)

tm_paused = False

# Função para substituir variáveis no HTML
def replace_variables(html, variables):
    gc.collect()
    print('replacing vars')
    for key, value in variables.items():
        gc.collect()
        html = html.replace(f'{{{{ {key} }}}}', str(value))
    print('end replacing vars')
    return html
      
# Função para ler arquivos
# CUIDADO ao alocar memoria, reserve pelo menos 250% do tamanho do arquivo
# Ex.: p/ um arquivo de 2kbytes reserve pelo menos 5kbytes
def read_file(filename, mode):
    gc.collect()
    print('reading files')
    with open(filename, mode) as file:
        print('end reading files')
        return file.read()

def html_response(html_request, wifi_isconnected, wifi_name, html_script):
        if html_request == WIFI_MANAGER_REQUEST:
            html_wifi_manager_content = read_file('static/wifi_manager.html', 'r')
            if wifi_isconnected :
                # Obtem nome da Wifi
                wifi_name = 'Wifi SSID: ' + wifi_name + '<br>'
                html_wifi_status = '<span style="color:green">Conectado!</span>'
            else :
                # Nome da Wifi vazio
                wifi_name = ''
                html_wifi_status = '<span style="color:red">Desconectado!</span>'
            # Injetando variáveis no HTML
            response = 'HTTP/1.1 200 OK\nContent-Type: text/html\n\n' + replace_variables(html_wifi_manager_content, {
                'clock': rtc_module.format_datetime(rtc_module.rtc.datetime()),
                'wifi_status': html_wifi_status,
                'wifi_name': wifi_name,
                'html_script': html_script
            })
            html_wifi_manager_content = None
        elif html_request == INDEX_REQUEST:
            html_index_content = read_file('static/index.html', 'r')
            if timers_module.active_light_mode == 'Vegetação':
                id = 3
            elif timers_module.active_light_mode == 'Floração':
                id = 4
            elif timers_module.active_light_mode == 'Germinação':
                id = 5

            if timers_module.light_state:
                light_state = 'Ligada'
            else:
                light_state = 'Desligada'

            if tm_paused == True:
                light_state += ' (pausado)'

            if timers_module.water_state:
                water_state = 'Ligado'
            else:
                water_state = 'Desligado'

            interval_days = []
            last_times = set()
            active_water_timers = timers_module.active_water_timers
            for n in active_water_timers:
               gc.collect()
               interval_days.append(int(timers_module.alarmes[int(n)]['dias_intervalo']))
               last_times.add(str(timers_module.alarmes[n]['dia_ultima_ativacao']) + '/'
                                 + str(timers_module.alarmes[n]['mes_ultima_ativacao']) + '/'
                                 + str(timers_module.alarmes[n]['ano_ultima_ativacao']) + '-'
                                 + str(timers_module.alarmes[n]['hora']) + ':'
                                 + str(timers_module.alarmes[n]['minuto']))
            active_water_timers = None
            l_start_time = rtc_module.format_time((timers_module.alarmes[id]['hora_inicio'], timers_module.alarmes[id]['minuto_inicio']))
            l_end_time = rtc_module.format_time((timers_module.alarmes[id]['hora_fim'], timers_module.alarmes[id]['minuto_fim']))

            if timers_module.boil_state:
                water_tank_sta = '<span style="color: green;">Cheio!</span>'
            else:
                water_tank_sta = '<span style="color: red;">VAZIO!</span>'
                
            gc.collect()
            response = 'HTTP/1.1 200 OK\nContent-Type: text/html\n\n' + replace_variables(html_index_content, {
                'clock': rtc_module.format_datetime(rtc_module.rtc.datetime()),
                'html_script': html_script,
                'irrigation_mode': 'Alarme Manual',
                'light_state': light_state,
                'light_mode': timers_module.active_light_mode,
                'irrigation_state': water_state,
                'active_water_timers': timers_module.active_water_timers,
                'last_times': last_times,
                'interval_days': interval_days,
                'light_start_time': l_start_time,
                'light_end_time': l_end_time,
                'water_tank_state': water_tank_sta
            })
            html_index_content = None
        elif html_request == LIGHT_SETTINGS_REQUEST:
            html_settings_content = read_file('static/light_configuration.html', 'r')
            response = 'HTTP/1.1 200 OK\nContent-Type: text/html\n\n' + replace_variables(html_settings_content, {
                'clock': rtc_module.format_datetime(rtc_module.rtc.datetime()),
                'active_light_mode': timers_module.active_light_mode,
                'html_script': html_script
            })
            html_settings_content = None
        elif html_request == WATER_SETTINGS_REQUEST:
            html_settings_content = read_file('static/irrigation_configuration.html', 'r')
            response = 'HTTP/1.1 200 OK\nContent-Type: text/html\n\n' + replace_variables(html_settings_content, {
                'clock': rtc_module.format_datetime(rtc_module.rtc.datetime()),
                'active_timers': timers_module.active_water_timers,
                'html_script': html_script
            })
            html_settings_content = None
        else:
            return None
        return response
