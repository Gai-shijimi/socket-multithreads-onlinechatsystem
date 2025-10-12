import socket
import threading
import queue


SERVER_ADDRESS = '127.0.0.1'
SERVER_PORT = 9000

q = queue.Queue()

def make_header_protocol(op, states, roomname, username):
    o = op.to_bytes(1, "big")
    s = states.to_bytes(1, "big")
    room = len(roomname.encode('utf-8')).to_bytes(4, "big")
    user = len(username.encode('utf-8')).to_bytes(4, "big")

    return o + s + room + user


def make_body(roomname, username):
    r = roomname.encode('utf-8')
    u = username.encode('utf-8')
    return r + u


def recv_state1_mssg(tcp_sock,):
    header = tcp_sock.recv(2)
    state = int.from_bytes(header[:1], "big")
    m_len = int.from_bytes(header[1:], "big")

    body = tcp_sock.recv(8)
    state = body[:state].decode('utf-8')
    message = body[state:state+m_len].decode('utf-8')

    print(f"状態：{state}, メッセージ:{message}")


def recv_state2_mssg(tcp_sock,):
    header = tcp_sock.recv(16)

    op = int.from_bytes(header[:1], "big")
    state = int.from_bytes(header[1:2], "big")
    room_len = int.from_bytes(header[2:3], "big")
    user_len = int.from_bytes(header[3:4], "big")
    mssg_len = int.from_bytes(header[4:8], "big")
    token_len =  int.from_bytes(header[8:], "big")

    body = tcp_sock.recv(64)
    roomname = body[:room_len].decode('utf-8')
    username = body[room_len:room_len+user_len].decode('utf-8')
    message = body[room_len+user_len: room_len+user_len+mssg_len].decode('utf-8')
    token = body[room_len+user_len+mssg_len: room_len+user_len+mssg_len+token_len].decode('utf-8')

    print(f"{roomname}, {username}, {message}, {token}")

    q.put(roomname)
    q.put(username)
    q.put(message)
    q.put(token)


def sender(sock, roomname, token):
    roomname_len = len(roomname).to_bytes(1, "big")
    token_size = len(token).to_bytes(1, "big")

    roomname_b = roomname.encode('utf-8')
    token_b = token.encode('utf-8')

    pre_payload = roomname_len + token_size + roomname_b + token_b

    while True:
        message = input("input message please")
        message_b = message.encode('utf-8')

        payload =  pre_payload + message_b
        sock.sendto(payload, (SERVER_ADDRESS, SERVER_PORT))


def receiver(sock):
    while True:
        data, _ = sock.recvfrom(4096)
        # username_len, username, message
        username_len = int.from_bytes(data[:1], "big")
        username = data[1:1+username_len].decode('utf-8')
        message = data[1+username_len:].decode('utf-8')

        print(f"{username}: {message}")
        

    


def main():
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)

    tcp_sock.connect((SERVER_ADDRESS, SERVER_PORT))

    # operation = input("部屋作成: 1, 部屋参加: 2 を入力してください")
    # roomname = input("部屋名を入力してください")
    # username = input("ユーザー名を入力してください")
    # curr_states = 0

    operation = 1
    curr_states = 0
    roomname = "testroom"
    username = "test1"
    

    header = make_header_protocol(operation, curr_states, roomname, username)
    tcp_sock.sendall(header)

    body = make_body(roomname, username)
    tcp_sock.sendall(body)

    recv_state1_mssg = threading.Thread(target=recv_state1_mssg, args=(tcp_sock, ))
    recv_state1_mssg.start()
    recv_state1_mssg.join()

    recv_state2_mssg = threading.Thread(target=recv_state2_mssg, args=(tcp_sock,))
    recv_state2_mssg.start()
    recv_state2_mssg.join()

    print("TCP通信を閉じます")
    tcp_sock.close()


    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    roomname = q.get()
    username = q.get()
    _ = q.get()
    token = q.get()

    receive = threading.Thread(target=receiver, args=(sock, ), daemon=True)
    receive.start()

    send = threading.Thread(target=sender, args=(sock, roomname, token), daemon=True)
    send.start()

    

