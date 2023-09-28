import Pyro4
import threading
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from sys import exit

Pyro4.config.SERIALIZERS_ACCEPTED = {'serpent', 'marshal'}
daemon = Pyro4.Daemon()
ns = None
server = None
name = None
games = {}

def threaded(func):
    def wrapper(*args, **kwargs):
        threading.Thread(target=func, args=args, kwargs=kwargs).start()
    return wrapper

@threaded
def listen2server():
    daemon.requestLoop()

@Pyro4.expose
class Game(tk.Toplevel):
    def __init__(self, master, oponent, mark, tab, game_id):
        menu.message('Jogo iniciado!')
        super().__init__(master)
        self.master = master
        self.window = None
        self.protocol('WM_DELETE_WINDOW', self.close_game)
        self.geometry('400x600')

        self.game_screen = tk.Canvas(self, height=600, width=200)
        self.game_screen.pack(side='left')

        self.chat_frame = tk.Frame(self, height=600, width=200)
        self.chat_frame.pack(side='right')

        ttk.Label(self.chat_frame, text=f'Usuário: {name}').pack(side='top')

        self.chat_view = ScrolledText(self.chat_frame, wrap=tk.WORD, height=20, width=50, state='disabled')
        self.chat_view.pack(padx=10, pady=5)

        self.chat_label = tk.Label(self.chat_frame, text='Chat:')
        self.chat_label.pack(padx=10, pady=5, side='left')

        self.entry = tk.Entry(self.chat_frame, width=50)
        self.entry.pack(padx=10, pady=5, side='right')

        self.game_screen.create_line(50, 0, 50, 150, width=3)
        self.game_screen.create_line(100, 0, 100, 150, width=3)
        self.game_screen.create_line(0, 50, 150, 50, width=3)
        self.game_screen.create_line(0, 100, 150, 100, width=3)

        self.game_screen.create_line(50, 200, 50, 350, width=3)
        self.game_screen.create_line(100, 200, 100, 350, width=3)
        self.game_screen.create_line(0, 250, 150, 250, width=3)
        self.game_screen.create_line(0, 300, 150, 300, width=3)

        self.game_screen.create_line(50, 400, 50, 550, width=3)
        self.game_screen.create_line(100, 400, 100, 550, width=3)
        self.game_screen.create_line(0, 450, 150, 450, width=3)
        self.game_screen.create_line(0, 500, 150, 500, width=3)

        self.label = ttk.Label(self, text='', font=("Arial", 10))
        self.label.place(x=50, y=550)

        self.button = ttk.Button(self, text='Desistir', command=self.forfeit)
        self.button.place(x=300, y=550)

        self.bind('<Button-1>', self.get_mouse)
        self.entry.bind('<Return>', self.input_entry)
        self.focus()

        self.oponent = oponent
        self.mark = mark
        self.tab = tab
        self.game_id = game_id
        self.over = False

        if self.mark == 'X':
            self.label['text'] = 'Você começa!'
            self.turn = True
        else:
            self.label['text'] = 'Oponente começa!'
            self.turn = False

    @threaded
    def draw(self, tab, p1, p2, mark):
        dis_x = p1 * 50
        dis_y = p2 * 50 + tab * 200
        if mark == 'X':
            self.game_screen.create_line(dis_x+5, dis_y+5, dis_x+45, dis_y+45, width=3, tags="game")
            self.game_screen.create_line(dis_x+45, dis_y+5, dis_x+5, dis_y+45, width=3, tags="game")
        elif mark == 'O':
            self.game_screen.create_oval(dis_x+5, dis_y+5, dis_x+45, dis_y+45, width=3, tags="game")
        self.pass_turn()

    def pass_turn(self):
        self.over = self.fim()
        if not self.over:
            if self.turn:
                self.label['text'] = 'Vez do oponente!'
                self.turn = False
            else:
                self.label['text'] = 'Sua vez!'
                self.turn = True
        else:
            self.button['text'] = 'Rematch'
            self.button['command'] = lambda: self.tab.rematch(self.oponent)

    def get_mouse(self, event):
        if not self.over:
            x = self.winfo_pointerx() - self.winfo_rootx()
            y = self.winfo_pointery() - self.winfo_rooty()
            print(x, y) # debug
            if self.turn:
                for pos in self.tab.pos_livres():
                    if x > pos[1] * 50 and x < (pos[1] + 1) * 50:
                        if y > (pos[0] * 200) + pos[2] * 50 and y < (pos[0] * 200) + (pos[2] + 1) * 50:
                            self.tab.insert(pos[0], pos[1], pos[2], self.mark)

    def fim(self):
        state = self.tab.avalia()
        if state == 1:
            if self.mark == 'X':
                self.label['text'] = 'Você venceu!'
            else:
                self.label['text'] = 'Você perdeu!'
            return True
        if state == -1:
            if self.mark == 'O':
                self.label['text'] = 'Você venceu!'
            else:
                self.label['text'] = 'Você perdeu!'
            return True
        if self.tab.tab_cheio():
            self.label['text'] = 'Empate!'
            return True
        return False
    
    @threaded
    def input_entry(self, event):
        msg = self.entry.get()
        if msg:
            self.entry.delete(0, tk.END)
            server.chat(msg, self.game_id)
            self.message(msg)

    def message(self, msg):
        self.chat_view['state'] = 'normal'
        self.chat_view.insert(tk.END, f'{name}: {msg}' + '\n')
        self.chat_view.see('end')
        self.chat_view['state'] = 'disabled'

    def forfeit(self, other=False):
        if not other:
            self.label['text'] = 'Você perdeu!'
            self.tab.forfeit(self.oponent)
        else:
            self.label['text'] = 'Oponente desistiu!'
        self.over = True
        self.button['text'] = 'Rematch'
        self.button['command'] = lambda: self.tab.rematch(self.oponent)

    @threaded
    def receive_rematch(self):
        if not self.window:
            self.window = tk.Toplevel(self.master)
            ttk.Label(self.window, text=f'{self.oponent} está requisitando um novo jogo!').pack()
            ttk.Button(self.window, text='Aceitar', command=lambda: [self.tab.restart(name, self.oponent), self.close_window()]).pack(padx=20, pady=10, side='left')
            ttk.Button(self.window, text='Recusar', command=self.close_window).pack(padx=20, pady=10, side='right')
            self.window.protocol('WM_DELETE_WINDOW', self.close_window)
            self.window.grab_set()

    @threaded
    def new_game(self, mark):
        self.game_screen.delete('game')
        self.over = False
        self.mark = mark
        self.button['text'] = 'Desistir'
        self.button['command'] = self.forfeit
        if self.mark == 'X':
            self.label['text'] = 'Você começa!'
            self.turn = True
        if self.mark == 'O':
            self.label['text'] = 'Oponente começa!'
            self.turn = False

    def close_window(self):
        if self.window:
            self.window.destroy()
            self.window = None

    def close_game(self, other=False):
        try:
            del games[self.game_id]
        except:
            pass
        if not other:
            self.tab.closed_game(name, self.oponent)
        self.destroy()

@Pyro4.expose
class Menu(tk.Frame):
    def __init__(self, master):
        global ns
        super().__init__(master)
        self.pack(side='top')
        self.master = master
        self.window = None

        self.title = ttk.Label(self, text='Chat TTT 3D')
        self.title.pack(padx=10, pady=10)

        self.menu_screen = ScrolledText(self, wrap=tk.WORD, height = 10, width=50, state = 'disabled')
        self.menu_screen.pack(padx=10, pady=10)

        self.buttons = [None, None, None, None]
        self.buttons[0] = ttk.Button(self, text='Iniciar Jogo')
        self.buttons[0].pack(padx=10)
        self.buttons[1] = ttk.Button(self, text='Listar usuários')
        self.buttons[1].pack(padx=10)
        self.buttons[2] = ttk.Button(self, text='Mudar nome')
        self.buttons[2].pack(padx=10)
        self.buttons[3] = ttk.Button(self, text='Sair')
        self.buttons[3].pack(padx=10)

        try:
            ns = Pyro4.locateNS()
        except:
            self.message('Servidor de nomes não iniciado!')
        else:
            self.login()
        
    @threaded
    def login(self):
        global name, server
        uri = daemon.register(self)
        self.message('Logando no servidor...')
        try:
            server = Pyro4.Proxy('PYRONAME:Server') # Inicia um protocolo de comunicação unidirecinal com o servidor
        except:
            self.message('Servidor não encontrado!')
            return
        name = server.start(uri)
        self.message(f'Logado como {name}')
        self.load_commands()
        self.master.protocol('WM_DELETE_WINDOW', self.disconnect)

    def load_commands(self):
        self.buttons[0]['command'] = self.new_game_invite
        self.buttons[1]['command'] = self.list_clients
        self.buttons[2]['command'] = self.change_name
        self.buttons[3]['command'] = self.disconnect

    def list_clients(self):
        self.clear_screen()
        for client in list(ns.list().keys())[2:]:
            self.message(str(client))
        self.message(f'Você é {name}')

    def clear_screen(self):
        self.menu_screen.config(state='normal')
        self.menu_screen.delete('1.0', tk.END)
        self.menu_screen.config(state='disabled')

    def change_name(self):
        if not self.window:
            self.window = tk.Toplevel(self.master)
            ttk.Label(self.window, text='Digite o seu novo nome').pack(padx=10)
            self.entry = ttk.Entry(self.window, width=50)
            self.entry.pack()
            ttk.Button(self.window, text='Confirmar', command=lambda: self.accept_name()).pack(padx=10)
            self.entry.bind('<Return>', lambda event: self.accept_name(event))
            self.window.protocol('WM_DELETE_WINDOW', self.close_window)
            self.entry.focus()
        else:
            self.window.focus_force()

    def game_invite(self):
        if not self.window:
            self.window = tk.Toplevel(self.master)
            ttk.Label(self.window, text='Digite o nome do oponente a convidar', width=50).pack(padx=10)
            self.entry = ttk.Entry(self.window, width=50)
            self.entry.pack(padx=10, pady=10)
            button = ttk.Button(self.window, text='Convidar', command=lambda: [server.send_invite(self.entry.get()), self.close_window()])
            button.pack()
            self.entry.bind('<Return>', lambda event: [self.send_invite_event(self.entry.get(), event), self.close_window()])
            self.window.protocol('WM_DELETE_WINDOW', self.close_window)
            self.entry.focus()
        else:
            self.window.focus_force()

    def new_game_invite(self):
        if not self.window:
            self.window = tk.Toplevel(self.master)
            self.window.protocol('WM_DELETE_WINDOW', self.close_window)
            self.window.focus()
            ttk.Label(self.window, text='Usuários disponíveis:').pack()
            listBox = tk.Listbox(self.window, width=50, height=10)
            listBox.pack()
            ttk.Button(self.window, text='Convidar', command=lambda: [server.send_invite(listBox.get(listBox.curselection()[0])), self.close_window()]).pack()
            listBox.bind('<Return>', lambda event: [self.send_invite_event(listBox.get(listBox.curselection()[0]), event), self.close_window()])
            for client in list(ns.list().keys())[2:]:
                if client != name:
                    listBox.insert(tk.END, client)
        else:
            self.window.focus_force()

    def send_invite_event(self, target, event):
        server.send_invite(target)

    @threaded
    def receive_invite(self, origin):
        if not self.window:
            self.window = tk.Toplevel(self.master)
            ttk.Label(self.window, text=f'{origin} está o convidando para uma partida!').pack()
            ttk.Button(self.window, text='Aceitar', command=lambda: [server.start_game(origin), self.close_window()]).pack(padx=20, pady=10, side='left')
            ttk.Button(self.window, text='Recusar', command=lambda: [server.refuse(origin), self.close_window()]).pack(padx=20, pady=10, side='right')
            self.window.grab_set()

    def accept_name(self, event=None):
        global name
        new_name = self.entry.get()
        if new_name == name:
            self.close_window()
            self.message('Este já é o seu nome!', cls=True)
        elif new_name:
            self.close_window()
            if server.change_name(new_name):
                name = new_name

    def start_game(self, oponent, mark, tab, game_id):
        global game
        game = Game(self.master, oponent, mark, tab, game_id)
        daemon.register(game)
        games[game_id] = game
        return game

    @threaded
    def game_message(self, msg, game_id):
        game = games[game_id]
        game.message(msg)

    @threaded
    def message(self, msg, cls=False):
        self.menu_screen.config(state='normal')
        if cls:
            self.menu_screen.delete('1.0', tk.END)
        self.menu_screen.insert(tk.END, msg + '\n')
        self.menu_screen.see('end')
        self.menu_screen.config(state='disabled')

    @threaded
    def close_window(self):
        self.window.destroy()
        self.window = None

    def disconnect(self):
        server.disconnect()
        self.master.quit()
        self.master.destroy()

root = tk.Tk()
root.title('Game')
menu = Menu(root)
listen2server()
root.mainloop()
exit()