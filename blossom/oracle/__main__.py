from getpass import getpass
from .client import check_connection, ConnectionFailure


def main():
    print('Teste de conexão — Oracle Primavera Cloud')
    print('Destino: https://primavera-us2.oraclecloud.com')
    print('As credenciais são usadas nesta execução; não são salvas em arquivo.')
    print('Nenhum projeto, WBS ou atividade será alterado.\n')
    try:
        username=input('Seu usuário/email Oracle: ')
        password=getpass('Sua senha Oracle (não aparece ao digitar): ')
        check_connection(username,password)
    except ConnectionFailure as exc:
        print('\nNão conectado: '+str(exc))
        return 1
    except (EOFError,KeyboardInterrupt):
        print('\nTeste cancelado.')
        return 1
    print('\nConexão confirmada pela API. Nenhum cronograma foi enviado.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
