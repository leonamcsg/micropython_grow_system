import time
from machine import Pin, Signal
import network

def execute() :
    # Escreve mensagem de boas vindas
    print("\033[2J\033[H", end='') # limpa terminal serial
    time.sleep(1)
    print("BEM VINDO AO SUPERGROW!")
    print("INICIANDO SISTEMA...\n")
    # Pino para ligar sensor
    pin13 = Pin(13, Pin.OUT)
    pin13.value(1)
    network.hostname('supergrow')
    network.country('BR')
    time.sleep(2)
    led_pin = Signal(pin13, invert=True)
    led_pin.value(1)
