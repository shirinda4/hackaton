import socket
import struct
from threading import *
import random
import time
import scapy.arch

UDP_DEST_PORT = 13117
MAGIC_COOKIE = 0xabcddcba
MESSAGE_TYPE = 0x2
MESSAGE_SIZE = 2048
my_tcp_port = 2022
# dest_tcp_port = 5000
UDP_IP = '127.0.0.1'



class Server:
    def __init__(self):
        self.server_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # tcp socket
        self.server_tcp_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.team_names = []
        self.games_threads = []
        self.local_udp_ip = UDP_IP
        self.local_tcp_ip = scapy.arch.get_if_addr("eth1")
        self.server_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # udp socket
        self.server_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # enable reuse address
        self.server_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # enable broatcat
        self.random_nums = self.generate_math_question()
        self.numConnected = 0
        self.is_answered = False
        self.is2connected = True
        self.winner = ""
        self.answering_lock = Lock()
        self.server_udp_socket.bind(('', UDP_DEST_PORT))
        self.client_answer = None
        self.winning_mess = ""
        self.answer = 0
        self.offer_thread = None
        self.recieve_thread = None
        self.server_tcp_socket.bind(('', my_tcp_port))

    def tear_down(self):
        self.is2connected = True
        self.winner = ""
        self.random_nums = self.generate_math_question()
        self.team_names =[]
        self.games_threads = []
        self.numConnected = 0
        self.is_answered = False
        self.server_tcp_socket.close()
        self.server_tcp_socket = None
        self.server_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # tcp socket
        self.server_tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_tcp_socket.bind(('', my_tcp_port))

    def Waiting_for_clients(self):

        try:
            print("Server started, listening on IP address ", self.local_udp_ip) #change

            offer_thread = Thread(target=self.broadcast_offers, daemon=True)
            offer_thread.start()
            recieve_thread = Thread(target=self.recieve_clients,daemon=True)
            recieve_thread.start()
            offer_thread.join()
            recieve_thread.join()

        except Exception as ex:
            print(ex)

    def generate_math_question(self):
        a = random.randint(0,9)
        b = random.randint(0,(9-a))
        self.answer = a+b
        return [a,b]


    def broadcast_offers(self):
        while self.is2connected:
                self.server_udp_socket.sendto((struct.pack('IBH', MAGIC_COOKIE, MESSAGE_TYPE, my_tcp_port)),('<broadcast>', UDP_DEST_PORT))
                time.sleep(1)

    def recieve_clients(self):
        self.server_tcp_socket.listen()
        while True:
            (conn, (dest_ip, dest_port)) = self.server_tcp_socket.accept()
            data = conn.recv(MESSAGE_SIZE).decode()  # get team name
            self.team_names.append([data,conn])
            game_thread = Thread(target=self.game_mode, daemon=True, args=[conn,data])
            self.games_threads.append(game_thread)
            self.numConnected = self.numConnected + 1
            if self.numConnected == 2:
                begin_thread = Thread(target=self.begin_game_threads,daemon=True)
                self.is2connected = False
                begin_thread.start()
                begin_thread.join()

                # for t in self.games_threads:
                #     t.join()
                if self.is_answered == False:
                    self.end_game()
                try:
                    self.team_names[0][1].send(self.winning_mess.encode())
                    self.team_names[1][1].send(self.winning_mess.encode())
                    self.team_names[0][1].close()
                    self.team_names[1][1].close()
                except Exception as ex:
                    pass

                print("Game over, sending out offer requests...")
                break
        self.tear_down()
        self.Waiting_for_clients()
    def begin_game_threads(self):
        for t in self.games_threads:
            t.start()
        time.sleep(10)
    def end_game(self):
        answer = self.random_nums[0] + self.random_nums[1]
        self.winning_mess = "Game Over!\n" + "The correct answer was " + str(answer) + "!!!\n" + "No team answered within 10 sec.\n" + "It's a Draw!" + self.team_names[0][
                                0] + "and " + self.team_names[1][0] + ", Try better next time :)\n"
    def game_mode(self,conn,team):
        # time.sleep(5)
        welcome_message = "Welcome to Quick Maths\n"+ "Player 1: "+ self.team_names[0][0]+ "Player 2: "+self.team_names[1][0]+ "\n=="
        answer = self.random_nums[0] + self.random_nums[1]
        math_question_message = "How much is "+ str(self.random_nums[0])+ "+"+ str(self.random_nums[1])
        conn.send(welcome_message.encode())
        conn.send(math_question_message.encode())
        try:
            client_answer = conn.recv(MESSAGE_SIZE).decode()
            self.client_answer = client_answer
        except Exception as ex:
            pass
        self.answering_lock.acquire()
        if(self.is_answered == False):

            if int(self.client_answer) == answer: #i won
                self.winner = team
                self.is_answered = True
            else:
                self.is_answered = True
                if(self.team_names[0][0] == team): #i lost - technical winning for other player
                    self.winner = self.team_names[1][0]
                else:
                    self.winner = self.team_names[0][0]
            self.winning_mess = "Game Over!"+"The correct answer was " + str(answer) + "!!!\n"+"Congratulations to the winner: " + self.winner

            self.answering_lock.release()




if __name__ == '__main__':
    s = Server()
    s.Waiting_for_clients()