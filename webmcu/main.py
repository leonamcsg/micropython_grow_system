import machine
import errno

from src import setup

import app
import timers_module
timers_module.deinit(False)

# Executa setup
setup.execute()

while True :
    try: # Inicia aplicativo
        app.execute()
    # Trata os erros OSErrors que subiram pra main
    except OSError as exc: 
        print(f'tipo do erro: {exc}')
        if exc.errno == errno.ECONNRESET:
            print('pedido de reinicio de comunicacao externo!')
        elif exc.errno == errno.EADDRINUSE:
            print('endereço em uso')
        print('reiniciando sistema...')
    # Trata erros de memoria
    except MemoryError as exc:
        print('Erro de alocacao de memoria')
        print('reiniciando sistema...')
    # Tratamento padrao
    except Exception as exc:
        print(f'tipo do erro: {exc}')
        print('reiniciando sistema...')
        raise exc
    machine.reset()
