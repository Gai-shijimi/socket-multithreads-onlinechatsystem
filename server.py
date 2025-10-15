import socket
import threading
import secrets
import string
import time

SERVER_ADDRESS = '127.0.0.1'
SERVER_PORT = 5000

U_SERVER_PORT = 5001


def tcp_listener(sock, lock, rooms):
    while True:
        try:
            conn, addr = sock.accept()
        except socket.error as e:
            print(e)
            break

        tcp_thread = threading.Thread(target=tcp_connection, args=(conn, addr, lock, rooms), daemon=True)
        tcp_thread.start()


def recv_exact(conn, protocol_size):
    buf = bytearray()
    while len(buf) < protocol_size:
        chunk = conn.recv(protocol_size - len(buf))
        if not chunk:
            raise ConnectionError("peer closed before reading enough bytes")
        buf.extend(chunk)
    return bytes(buf)


# op, states, roomname, username
def request_analysis(header_cont, conn):
    protocol_size = 10
    header = recv_exact(conn, protocol_size)
    op_code = int.from_bytes(header[0:1], "big")
    status = int.from_bytes(header[1:2], "big")
    roomname = int.from_bytes(header[2:6], "big")
    username = int.from_bytes(header[6:10], "big")

    header_cont.append(op_code)
    header_cont.append(status)
    header_cont.append(roomname)
    header_cont.append(username)
    

def body_analysis(b_cont, h_cont, conn):
    payload_size = h_cont[2] + h_cont[3]
    body = recv_exact(conn, payload_size)
    roomname = body[:h_cont[2]].decode('utf-8')
    username = body[h_cont[2]: h_cont[2]+h_cont[3]].decode('utf-8')
    b_cont.append(roomname)
    b_cont.append(username)

def is_roomname_registered(roomname, lock, rooms):
    with lock:
        if roomname not in rooms:
            return False
        else:
            return True
        
def generate_token(length=32):
    alphabet = string.ascii_letters + string.digits
    token = ''.join(secrets.choice(alphabet) for _ in range(length))

    return token


def add_info_to_rooms(header_cont, body_cont, token, rooms, lock):
    roomname = body_cont[0]
    username = body_cont[1]
    flag = True
    if not rooms.get(roomname):
        flag = False
    with lock:
        if not flag and header_cont[0] == 1:
            rooms = {
                roomname: {
                    "users":{
                        token: {
                            "token": token,
                            "username": username, 
                            "id": "host",
                            "udp":None,
                            }
                    }
                }
            }

        elif header_cont[0] == 2:
            rooms[roomname]["users"][token]["token"] = token
            rooms[roomname]["users"][token]["username"] = username
            rooms[roomname]["users"][token]["id"] = "member"
            rooms[roomname]["users"][token]["udp"] = None


def main_mssg_handler(header_cont, body_cont, token, conn):
    message = "状態0の解析完了, state:1"
    state1_message_send = threading.Thread(target=s1_mssg_handler, args=(header_cont, message, conn))
    state1_message_send.start()
    state1_message_send.join()

    message = "サーバー側においてルーム作成の処理は成功しました。"
    states2_message_send = threading.Thread(target=s2_mssg_handler, args=(header_cont, body_cont, message, token, conn))
    states2_message_send.start()
    states2_message_send.join()
        


def s1_mssg_handler(h_cont, message, conn):
    h_cont[1] = 1
    state = h_cont[1].to_bytes(1, "big")
    m = message.encode('utf-8')

    len_m = len(m).to_bytes(7, "big")
    header = state + len_m
    conn.sendall(header)

    conn.sendall(m)


def s2_mssg_handler(h_cont, b_cont, message, token, conn):
    h_cont[1] = 2

    op = h_cont[0]
    state = h_cont[1]
    roomname = b_cont[0]
    username = b_cont[1]

    print(f"op: {op}")
    print(f"state: {state}")
    print(f"roomname: {roomname}")
    print(f"username: {username}")

    room_len = len(roomname.encode("utf-8")).to_bytes(4, "big")
    user_len = len(username.encode('utf-8')).to_bytes(4, "big")
    mssg_len = len(message.encode('utf-8')).to_bytes(4, "big")
    token_len = len(token.encode('utf-8')).to_bytes(4, "big")

    print(f"room_len: {room_len}")
    print(f"user_len: {user_len}")
    print(f"mssg_len: {mssg_len}")
    print(f"token_len: {token_len}")

    # op:1, state:1, room_len:4, user_len:4, mssg_len:4, token_len:4
    header = op.to_bytes(1, "big") + state.to_bytes(1, "big") + room_len + user_len + mssg_len + token_len

    conn.sendall(header)


    room_b = roomname.encode('utf-8')
    user_b = username.encode('utf-8')
    mssg_b = message.encode('utf-8')
    token_b = token.encode('utf-8')

    body = room_b + user_b + mssg_b + token_b

    conn.sendall(body)

def tcp_connection(conn, addr, lock, rooms):
    print("接続完了")

    # header: 0 operation, 1 states, 2 roomname, 3 username
    header_cont = []
    request_analysis(header_cont, conn)

    # body_con: 0 roomname, 1 username
    body_cont = []
    body_analysis(body_cont, header_cont, conn)

    # flag = Falseはルーム名が登録されていない
    flag = is_roomname_registered(body_cont[0], lock, rooms)

    # 部屋作成コード1
    if header_cont[0] == 1 and header_cont[1] == 0:
        token = generate_token()

        if flag == True:
            print("エラーメッセージ")
            # ルームは作成されている、参加? エラーメッセージを送信
        else:
            add_info_to_rooms(header_cont, body_cont, token, rooms, lock)

            main_mssg_handler(header_cont, body_cont, token, conn)

            time.sleep(10)
            print("TCP通信のソケットを閉じます。")
            conn.close()
        
    
    # 部屋参加コード 2
    elif header_cont[0] == 2 and header_cont[1] == 0:
        token = generate_token()

        # 部屋が存在するか
        if flag == False:
            print("部屋がありません。ルーム作成してください。")

        else:
            add_info_to_rooms(header_cont, body_cont, token, rooms)

            main_mssg_handler(header_cont, body_cont, token, conn)

            print("TCP通信のソケットを閉じます")
            conn.close()


def get_username(rooms, roomname, token, lock):
    with lock:
        for user in rooms[roomname]["users"]:
            if user[token]["token"] == token:
                return user[token]["username"]
        
def valid_token(rooms, roomname, token, lock):
    with lock:
        for user in rooms[roomname]["users"]:
            if user[token]["token"]== token:
                return True
        
        return False

def update_user_info(rooms, roomname, token, username, addr, lock):
    with lock:
        role = rooms[roomname]["users"][token]["id"]
        rooms[roomname]["users"][token].update({"token":token, "username":username, "id": role, "udp": addr})

            

def udp_listener(sock, rooms, lock):
    print("UDP通信を開始します")
    while True:
        data, client_addr = sock.recvfrom(4096)
        #roomname, token, message
        roomname_len = int.from_bytes(data[:1], "big")
        token_len = int.from_bytes(data[1:2], "big")
        roomname = data[2:2+roomname_len].decode("utf-8")
        token = data[2+roomname_len:2+roomname_len+token_len].decode('utf-8')
        message = data[2+roomname_len+token_len:].decode('utf-8')

        username = get_username(rooms, roomname, token, lock)

        update_user_info(rooms, roomname, token, username, client_addr, lock)

        print(f"クライアントからのメッセージ受信：{roomname}, {username}, {token}, {message}")

        is_valid = valid_token(rooms, roomname, token, lock)

        username_len = len(username).to_bytes(1, "big")
        username_b = username.encode('utf-8')
        message_b = message.encode('utf-8')
        payload = username_len + username_b + message_b

        if is_valid:
            for token in rooms[roomname]["users"].keys():
                sock.sendto(payload, token["udp"])
        else:
            print("Error")
                

def main():
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    tcp_sock.bind((SERVER_ADDRESS, SERVER_PORT))
    tcp_sock.listen(10)
    print("サーバー待機中....")

    rooms = {}
    lock = threading.Lock()
    tcp_thread = threading.Thread(target=tcp_listener, args=(tcp_sock, lock, rooms), daemon=True)
    tcp_thread.start()

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((SERVER_ADDRESS, U_SERVER_PORT))
    udp_thread = threading.Thread(target=udp_listener, args=(udp_sock,rooms, lock), daemon=True)
    udp_thread.start()

    threading.Event().wait()



if __name__ == "__main__":
    main()
    