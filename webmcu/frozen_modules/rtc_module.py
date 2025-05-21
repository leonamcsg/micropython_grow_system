# rtc_module - testando e ultilizado com esp8266 - autor: leonam C S Gomes + chatgpt :)
from machine import RTC
import socket
import json
import struct
import time

# Real Time Clock - Valor padrão inicial para o relógio
GMT_OFFSET = - 3 * 3600   # timezone UTC-3
NTP_HOST = 'pool.ntp.org'
rtc = RTC()

NTP_TIMEOUT = 3
N_TIMES = 3

# Função para formatar o tempo
def format_datetime(t):
    return "{:02}/{:02}/{:04} {:02}:{:02}:{:02}".format(t[2], t[1], t[0], t[4], t[5], t[6])

def format_time(t):
    return "{:02}:{:02}".format(int(t[0]), int(t[1]))

def salvar_ntp():
    print('Salvando relogio ntp...')
    data = rtc.datetime()
    with open('/config/ntp_data.json', 'w') as f:
        json.dump(data, f)
    print('Relogio ntp salvo com sucesso.')

# função para carregar estado dos alarmes
def carregar_ntp():
    try:
        print('Carregando ntp...')
        with open('/config/ntp_data.json', 'r') as f:
            data = json.load(f)
        rtc.datetime(data)
        print('Relogio ntp carregado com sucesso.')
    except OSError:
        print('Nenhuma configuração encontrada, usando valores padroes.')
        # Defina os valores padrão se o arquivo não existir
        # Ano, Mês, Dia, Dia da semana, Hora, Minuto, segundos, ms
        rtc.datetime(2024, 1, 1, 0, 0, 0, 0, 0)
 
# Função para conectar com servidor NTP
def ntp_connect():
    NTP_DELTA = 3155673600
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    n = 0
    success = False
    # Faz 3 tentativas de conexão
    while (n < N_TIMES) and (success == False) :
        try:
            addr = socket.getaddrinfo(NTP_HOST, 123)[0][-1]
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except Exception as exc:
            print("Erro de conexao do socket!")
            n = N_TIMES # Pula verificação e retorna falha
        
        # Tentar sincronizar com o servidor NTP
        try:
            print('Sincronizando relogio com NTP...')
            s.settimeout(NTP_TIMEOUT) # Aguarda NTP_TIMEOUT segundos
            res = s.sendto(NTP_QUERY, addr)
            msg = s.recv(48)
            s.close()
            success = True
            n = N_TIMES
        except Exception as e:
            print('Falha ao sincronizar com NTP:', e)
            print('Tentando novamente...')
            success = False
        n += 1

    if success :
        ntp_time = struct.unpack("!I", msg[40:44])[0]
        tm = time.gmtime(ntp_time - NTP_DELTA + GMT_OFFSET)
        rtc.datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
        print('Relogio sincronizado:', format_datetime(rtc.datetime()))
        salvar_ntp()
    else:
        print('Não foi possivel sincronizar com NTP')
        print('Setting initial time...')
        carregar_ntp()
        print('Time set to initial value:', format_datetime(rtc.datetime()))
