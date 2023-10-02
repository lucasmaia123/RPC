import Pyro4
import Pyro4.naming
import threading
from random import randint, choices
from numpy import array
from copy import deepcopy
import string

clients = {}
games = {}
guest_number = 0
S = threading.Semaphore(1)

def threaded(func):
    def wrapper(*args, **kwargs):
        threading.Thread(target=func, args=args, kwargs=kwargs).start()
    return wrapper

@threaded
def start_ns():
    print('Inicializando servidor de nomes...')
    Pyro4.naming.startNSloop()

def id_generator(size):
    return ''.join(choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=size))

@Pyro4.expose
class Tabuleiro:
    def __init__(self, game_id):
        self._tab = self.gera_tabuleiro()
        self.players = {}
        self.game_id = game_id

    def get_tab(self):
        return self._tab
    
    def del_tab(self):
        del self._tab
        self._tab = self.gera_tabuleiro()

    def gera_tabuleiro(self):
        return [[[None, None, None] for i in range(3)] for j in range(3)]

    def pos_livres(self):
        return [[k,i,j] for k in range(3) for i in range(3) for j in range(3) if self._tab[k][i][j] == None]
    
    def pos_mark(self):
        return [[k,i,j] for k in range(3) for i in range(3) for j in range(3) if self._tab[k][i][j] != None]
    
    @threaded
    def insert(self, p1, p2, p3, mark):
        self._tab[p1][p2][p3] = mark
        self.avalia()
        for player in self.players.values():
            S.acquire()
            player.draw(p1, p2, p3, mark)
            S.release()

    def tab_vazio(self):
        for k in range(3):
            for i in range(3):
                for j in range(3):
                    if self._tab[k][i][j] != None:
                        return False
        return True
    
    def tab_cheio(self):
        for k in range(3):
            for i in range(3):
                for j in range(3):
                    if self._tab[k][i][j] == None:
                        return False
        return True

    @threaded
    def vitoria(self, winner, loser):
        S.acquire()
        self.players[winner].result(True)
        self.players[loser].result(False)
        S.release()

    # Checa se alguem venceu
    @threaded
    def avalia(self):
        visitados = []
        for pos in self.pos_mark():
            atual = [pos[0], pos[1], pos[2]]
            mark = self._tab[pos[0]][pos[1]][pos[2]]
            visitados.append(atual)
            vizinhos = self.neighbors(atual, visitados)
            # Analisa os elementos vizinhos e checa se eles formam uma reta
            for v in vizinhos:
                if self._tab[v[0]][v[1]][v[2]] == mark:
                    passo = array(v) - array(atual)
                    next = array(v) + passo
                    try:
                        if self._tab[next[0]][next[1]][next[2]] == mark:
                            winner = mark
                            for player in self.players.values():
                                S.acquire()
                                player.fim(winner)
                                S.release()
                            return
                    except:
                        continue
            if self.tab_cheio():
                for player in self.players.values():
                    player.fim(None)

    # Algoritimo para criar uma lista de possiveis vetores de n dimenções com tamanho definido 
    # Exemplo: (1, 0, 0) <- primeiro vetor de 3 dimenções com tamanho 1
    def permutations(self, val, size):
        aux = []
        perms = []
        for i in range(size):
            aux.append(0)
        perms.append(aux)
        for i in range(size):
            for k in range(len(perms)):
                aux = self.permute(val, perms[k])
                for j in aux:
                    if j not in perms:
                        perms.append(j)
        perms.pop(0)
        return perms

    # Gera novos vetores baseado em um vetor inicial ao adicionar o vetor de possíveis permutações vetoriais
    # Usado como auxiliar para o algoritimo acima
    def permute(self, val, lista):
        perms = []
        # Insere o tamanho do vetor normal e invertido em cada dimenção do vetor para gerar novos vetores
        for i in range(len(lista)):
            if lista[i] != val:
                lista[i] = val
                perms.append(deepcopy(lista))
                lista[i] = val * -1
                perms.append(deepcopy(lista))
                lista[i] = 0
        return perms
        
    # Pega os possiveis elementos vizinhos de um espaço no tabuleiro
    def neighbors(self, pos, visitados):
        n = []
        moves = self.permutations(1, 3) # Utiliza possíveis vetores de tamanho 1 para encontrar elementos vizinhos
        for move in moves:
            n_pos = array(pos) + array(move)
            if list(n_pos) not in visitados and (n_pos >= 0).all() and (n_pos < 3).all():
                n.append(n_pos)
        return n
    
    @threaded
    def restart(self, p1, p2):
        self._tab = self.gera_tabuleiro()
        n = randint(1, 100)
        S.acquire()
        if n > 50:
            self.players[p1].new_game('X')
            self.players[p2].new_game('O')
        else:
            self.players[p1].new_game('O')
            self.players[p2].new_game('X')
        S.release()

    @threaded
    def forfeit(self, oponent):
        S.acquire()
        self.players[oponent].forfeit(other=True)
        S.release()

    @threaded
    def rematch(self, oponent):
        S.acquire()
        self.players[oponent].receive_rematch()
        S.release()

    @threaded
    def closed_game(self, origin, oponent):
        S.acquire()
        oponent_ref = clients[oponent]
        self.players[oponent].close_game(other=True)
        oponent_ref.message(f'{origin} saiu do jogo!')
        S.release()
        try:
            del games[self.game_id]
        except:
            pass

@Pyro4.expose
class Client:

    name = ''
    client = None

    def start(self, uri):
        global guest_number
        guest_number+=1
        self.name = f'guest{guest_number}'
        ns.register(self.name, uri)
        self.client = Pyro4.Proxy(uri) # Inicia um protocolo de comunicação unidirecinal com o cliente
        clients[self.name] = self.client
        print(f'{self.name} se conectou!\nUri: {uri}')
        return self.name
    
    @threaded
    def start_game(self, oponent):
        oponent_ref = clients[oponent]
        game_id = id_generator(20)
        tab = Tabuleiro(game_id)
        daemon.register(tab)
        self.client.message(f'Iniciando jogo com {oponent}...', cls=True)
        oponent_ref.message(f'Iniciando jogo com {self.name}...', cls=True)
        n = randint(1, 100)
        S.acquire()
        if n > 50:
            player1 = self.client.start_game(oponent, 'X', tab, game_id)
            player2 = oponent_ref.start_game(self.name, 'O', tab, game_id)
            tab.players[self.name] = player1
            tab.players[oponent] = player2
        else:
            player1 = self.client.start_game(oponent, 'O', tab, game_id)
            player2 = oponent_ref.start_game(self.name, 'X', tab, game_id)
            tab.players[self.name] = player1
            tab.players[oponent] = player2
        S.release()
        games[game_id] = [tab, self.name, oponent]

    def chat(self, msg, game_id):
        for client in games[game_id][1:]:
            if client != self.name:
                client_ref = clients[client]
                client_ref.game_message(msg, game_id)

    def change_name(self, new_name):
        try:
            ns.lookup(new_name)
        except:
            if new_name[:5] == 'guest':
                self.client.message('Nome inválido', cls=True)
                return False
            uri = ns.lookup(self.name)
            ns.remove(self.name)
            ns.register(new_name, uri)
            clients[new_name] = clients.pop(self.name)
            print(f'{self.name} trocou de nome para {new_name}')
            self.name = new_name
            self.client.message(f'Seu novo nome é {new_name}', cls=True)
            return True
        else:
            self.client.message('Este nome já existe!', cls=True)
            return False
        
    def send_invite(self, target):
        if target:
            if target == self.name:
                self.client.message('Você não pode convidar a si mesmo!')
                return
            try:
                target_ref = clients[target]
                target_ref.receive_invite(self.name)
            except:
                self.client.message(f'{target} não existe!')

    def refuse(self, target):
        if target:
            try:
                target_ref = clients[target]
                target_ref.message(f'{self.name} recusou seu convite!')
            except:
                self.client.message('Usuário não encontrado!')

    def disconnect(self):
        ns.remove(self.name)
        del clients[self.name]
        print(f'{self.name} se desconectou!')
        del self


start_ns()
daemon = Pyro4.Daemon()
uri = daemon.register(Client)
ns = Pyro4.locateNS()
ns.register('Server', uri)
print('Servidor inicializado!')
daemon.requestLoop()