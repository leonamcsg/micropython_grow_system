# timer_module - testando e ultilizado com esp8266 - autor: leonam C S Gomes + chatgpt :)
from machine import Pin, Timer, Signal, ADC
import gc
import json
import rtc_module # frozen module
import sm_module

gc.enable()

# Importa relógio do módulo
rtc = rtc_module.rtc

# Variáveis globais
alarms_changed = True
active_light_mode = ''
active_water_timers = {}
# Pino único para irrigação
w_pin = 1
pin5 = Pin(5, Pin.OUT)
pin5.value(1)
water_pin = Signal(pin5, invert=True)
water_state = None
# Pino para iluminação
l_pin = 0
pin4 = Pin(4, Pin.OUT)
pin4.value(1)
light_pin = Signal(pin4, invert=True)
light_state = None
# Pino para ligar sensor
sm_pin = 2
pin14 = Pin(14, Pin.OUT)
pin14.value(0)
soil_m_pin = Signal(pin14, invert=True)
soil_m_state = None

# Pino boia
pin12 = Pin(12, Pin.IN, Pin.PULL_UP)
boil_state = pin12.value()

# Pino ADC
adc = ADC(0)

# TIMERS
tm = Timer(0) # Cria timer principal
tm_period = 20000

ntp_tm = Timer(1) # Cria timer de atualizacao do relogio rtc com servidor ntp
ntp_period=5400000 # 1:30 horas

# Timer para desligar após duracao_ms
# Importante ultilizar o mesmo Timer p/ os alarmes, caso virtual alocar externamente
tm_one_shot = Timer(2)

# Timer para verificar humidade do solo
sm_tm = Timer(-1)
sm_period = 3600000 # 1 hora
sm_one_shot = Timer(-1)

# função para salvar estado dos alarmes
def salvar_alarmes(): 
    print('Salvando alarmes...')
    data = {
        'alarmes': alarmes,
        'active_light_mode': active_light_mode,
        'active_water_timers': list(active_water_timers)  # Converta para lista para salvar
    }
    with open('/config/alarme_config.json', 'w') as f:
        json.dump(data, f)
    print('Alarmes e estados salvos com sucesso.')
    gc.collect()

# função para carregar estado dos alarmes
def carregar_alarmes():
    global alarmes, active_light_mode, active_water_timers
    gc.collect()
    try:
        print('Carregando alarmes...')
        with open('/config/alarme_config.json', 'r') as f:
            data = json.load(f)
            print(data)  # Adiciona essa linha para verificar o conteúdo do JSON
            alarmes = data['alarmes']  # Acessa o dicionário
            active_light_mode = data.get('active_light_mode', 'Vegetação')  # Pega o valor usando a chave 'active_light_mode'
            active_water_timers = set(data.get('active_water_timers', {0}))  # Converte de volta para set
        print('Alarmes e estados carregados com sucesso.')
    except OSError:
        print('Nenhum arquivo de configuração encontrado, usando valores padrão.')
        # Defina os valores padrão para os alarmes se o arquivo não existir
        alarmes = [
            {'tipo': 'irrigacao', 'dias_intervalo': 0, 'hora': 17, 'minuto': 0, 'duracao_ms': 3000, 'dia_ultima_ativacao': 0, 'mes_ultima_ativacao': 0, 'ano_ultima_ativacao': 0}, # Timer0 de Irrigação
            {'tipo': 'irrigacao', 'dias_intervalo': 1, 'hora': 12, 'minuto': 0, 'duracao_ms': 3000, 'dia_ultima_ativacao': 0, 'mes_ultima_ativacao': 0, 'ano_ultima_ativacao': 0}, # Timer1 de Irrigação
            {'tipo': 'irrigacao', 'dias_intervalo': 2, 'hora': 0, 'minuto': 30, 'duracao_ms': 3000, 'dia_ultima_ativacao': 0, 'mes_ultima_ativacao': 0, 'ano_ultima_ativacao': 0}, # Timer2 de Irrigação
            {'tipo': 'iluminacao', 'modo': 'Vegetação', 'hora_inicio': 5, 'minuto_inicio': 0, 'hora_fim': 23, 'minuto_fim': 0}, # Iluminação
            {'tipo': 'iluminacao', 'modo': 'Floração', 'hora_inicio': 6, 'minuto_inicio': 0, 'hora_fim': 18, 'minuto_fim': 0}, # Iluminação
            {'tipo': 'iluminacao', 'modo': 'Germinação', 'hora_inicio': 0, 'minuto_inicio': 0, 'hora_fim': 22, 'minuto_fim': 0}, # Iluminação
        ]
        active_light_mode = 'Vegetação'
        active_water_timers = {0}
        
def atualizar_ultima_ativacao(alarme, dia, mes, ano):
    gc.collect()
    alarme['dia_ultima_ativacao'] = dia
    alarme['mes_ultima_ativacao'] = mes
    alarme['ano_ultima_ativacao'] = ano
    salvar_alarmes()

# Função para ligar ou desligar um pino
def controlar_pino(pino, estado):
    global light_state
    global water_state
    if pino == w_pin:
        water_pin.value(estado)
        water_state = estado
        print(f'Pino {pin5} {"ativo" if water_state else "desligado"}')
    elif pino == l_pin:
        light_pin.value(estado)
        light_state = estado
        print(f'Pino {pin4} {"ativo" if light_state else "desligado"}')
    elif pino == sm_pin:
        soil_m_pin.value(estado)
        print("Estado do sensor de umidade:", estado)
    else:
        print("ERRO! Deu ruim em controlar_pino!")
# Função para calcular o número de dias em um mês
def dias_no_mes(mes, ano):
    if mes in [1, 3, 5, 7, 8, 10, 12]:
        return 31
    elif mes in [4, 6, 9, 11]:
        return 30
    elif mes == 2:
        # Verifica se o ano é bissexto
        if (ano % 4 == 0 and ano % 100 != 0) or (ano % 400 == 0):
            return 29
        else:
            return 28
    return 0

# Função para verificar se o alarme de irrigação deve ser ativado
def deve_ativar_irrigacao(alarme, now):
    gc.collect()
    dia_atual = int(now[2])
    mes_atual = int(now[1])
    ano_atual = int(now[0])

    dia_ultima_ativacao = int(alarme['dia_ultima_ativacao'])
    mes_ultima_ativacao = int(alarme['mes_ultima_ativacao'])
    ano_ultima_ativacao = int(alarme['ano_ultima_ativacao'])
    dias_intervalo = int(alarme['dias_intervalo'])

    if mes_atual == mes_ultima_ativacao and ano_atual == ano_ultima_ativacao:
        dias_desde_ultima_ativacao = dia_atual - dia_ultima_ativacao
    else:
        dias_no_ultimo_mes = dias_no_mes(mes_ultima_ativacao, ano_ultima_ativacao)
        dias_desde_ultima_ativacao = (dias_no_ultimo_mes - dia_ultima_ativacao) + dia_atual

    # Se o intervalo de dias não foi cumprido, não ativa
    if dias_desde_ultima_ativacao <= dias_intervalo:
        # Calcula a próxima data de ativação
        proxima_ativacao_dia = dia_ultima_ativacao + dias_intervalo
        proximo_mes = mes_ultima_ativacao
        proximo_ano = ano_ultima_ativacao

        # Ajusta para o próximo mês ou ano, se necessário
        dias_no_mes_atual = dias_no_mes(mes_ultima_ativacao, ano_ultima_ativacao)
        if proxima_ativacao_dia > dias_no_mes_atual:
            proxima_ativacao_dia -= dias_no_mes_atual
            proximo_mes += 1
            if proximo_mes > 12:
                proximo_mes = 1
                proximo_ano += 1

        print('Timer ja foi acionado! Ultima ativacao: ' + str(dia_ultima_ativacao) + '/' + str(mes_ultima_ativacao) + '/' + str(ano_ultima_ativacao))
        print('Proxima ativacao prevista para: ' + str(proxima_ativacao_dia) + '/' + str(proximo_mes) + '/' + str(proximo_ano))
        return False

    # Atualiza a última ativação
    atualizar_ultima_ativacao(alarme, dia_atual, mes_atual, ano_atual)
    print("Timer acionado!")
    print("Timer salvos")
    gc.collect()
    return True

# Função para lidar com os alarmes
# CUIDADO: Nao e possivel alocar memoria usando modulos importado durante callback
# Ex.: timer principal e de irrigacao são alocados como variaveis globais
def timer_callback(t):  # Timer object é passado pelo argumento t
    gc.collect()
    print('Timer interrupt called')
    global alarms_changed
    global boil_state
    
    now = rtc.datetime()
    hora_atual = int(now[4])
    minuto_atual = int(now[5])
    n = 0
    for alarme in alarmes:
        if alarme['tipo'] == 'irrigacao':
            # Verifica se o horário de irrigação já passou e ativa a irrigação
            if ((hora_atual > int(alarme['hora']) or (hora_atual == int(alarme['hora'])
            and minuto_atual >= int(alarme['minuto']))) and (n in active_water_timers)):
                print('verificando timer: Timer'+ str(n) + '!')
                if deve_ativar_irrigacao(alarme, now):
                    water_one_shot(alarme['duracao_ms']) # Liga a irrigação usando duração especifica

        elif alarme['tipo'] == 'iluminacao' and active_light_mode == alarme['modo']:
            print('verificando modo de iluminacao: '+ alarme['modo'] + '!')
            # Verifica se o horário de início já passou e o horário de fim ainda não passou
            if (((hora_atual > int(alarme['hora_inicio'])) or ((hora_atual == int(alarme['hora_inicio'])) 
            and (minuto_atual >= int(alarme['minuto_inicio'])))) and ((hora_atual < int(alarme['hora_fim']))
            or ((hora_atual == int(alarme['hora_fim'])) and (minuto_atual <= int(alarme['minuto_fim']))))):
                controlar_pino(l_pin, 1)  # Liga a iluminação
            else:
                controlar_pino(l_pin, 0)  # Desliga a iluminação fora do horário
        n = n + 1
    if alarms_changed == True : # Atualiza alarmes se houve alteração pelo usuario
        alarms_changed = False
        salvar_alarmes()
        
    # Verifica boia de nivel do reservatorio
    print('Verificando nivel do reservatorio...')
    if boil_state != pin12.value():
        print('Detectada alteração no nivel do reservatorio.')
    boil_state = pin12.value()
    if boil_state: # Se 1 reservatorio esta cheio
        print('Reservatorio cheio!')
    else:
        print('RESERVATORIO VAZIO!')

def ntp_callback(t):
    gc.collect()
    rtc_module.ntp_connect()

# interrupção para analise da humidade do solo
def sm_callback(t):
    print('Verificando sensor de umidade do solo...')
    # realiza medição
    controlar_pino(sm_pin, 0)
    sm_one_shot.init(period=1000 , mode=Timer.ONE_SHOT, callback=lambda t: sm_run())

def sm_run():
    conf = sm_module.config()
    if conf == None:
        moisture, raw = sm_module.read(adc)
    else:
        moisture, raw = sm_module.read(adc, conf['calibrationAir'], conf['calibrationWater'])

    # salva dados internamente
    datetime = rtc_module.rtc.datetime() # verifica data e horário
    sm_module.save_internal((moisture, raw, datetime))
    controlar_pino(sm_pin, 1)
    print("Umidade: %.0f%% - [ADC: %d] - %s" % (moisture, raw, rtc_module.format_datetime(datetime)))

def water_one_shot(duracao_ms):
    # Liga a irrigação
    controlar_pino(w_pin, 1)
    # Timer é alocado externamente pois nao é possivel alocar memoria durante callback
    # CUIDADO: É nescessário usar um sistema de segurança caso o alarme não desligue, evite transbordamento de água
    tm_one_shot.init(period=duracao_ms , mode=Timer.ONE_SHOT, callback=lambda t: controlar_pino(w_pin, 0))

def init(only_tm: bool):
    carregar_alarmes()  # Carrega os alarmes e estados do arquivo
    salvar_alarmes()  # Salva o estado inicial
    gc.collect()
    if not only_tm:
        # Chama callback ao iniciar
        ntp_callback(ntp_tm)
        sm_callback(sm_tm)
        # Configura o timer para chamar timer_callback
        ntp_tm.init(period=ntp_period, callback=ntp_callback)
        sm_tm.init(period=sm_period, callback=sm_callback)

    # Chama callback ao iniciar
    timer_callback(tm)
    # Configura o timer para chamar timer_callback a cada 'tm_period' segundos
    tm.init(period=tm_period, callback=timer_callback)

def deinit(only_tm: bool):
    gc.collect()
    if not only_tm:
        ntp_tm.deinit()
        sm_tm.deinit()
    # Desliga timer principal
    tm.deinit()
