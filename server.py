import socket
import secrets
import string
from datetime import datetime, timedelta
import threading 


def make_header(roomname, operation_code, states, username, message):
    roomname_bits = roomname.encode('utf-8')
    roomname_len = len(roomname_bits)
    roomnamelen_bytes_count = roomname_len.to_bytes(4, "big")

    operation_code_bytes_count = operation_code.to_bytes(1, "big")

    states_bytes_count = states.to_bytes(1, "big")

    username_bits = username.encode('utf-8')
    username_len = len(username_bits)
    usernamelen_bytes_count = username_len.to_bytes(4, "big")
    message_bits = message.encode('utf-8')
    len_bytes_message = len(message_bits)
    messagelen_bytes_count = len_bytes_message.to_bytes(4, "big")

    return roomnamelen_bytes_count + operation_code_bytes_count + states_bytes_count + usernamelen_bytes_count + messagelen_bytes_count


# 12バイトのヘッダー
def make_header_for_complite(roomname, operation, states, username, message, token):
    roomname_bits = roomname.encode('utf-8')
    roomname_len = len(roomname_bits)
    roomnamelen_bytes_count = roomname_len.to_bytes(4, "big")

    operation_code_bytes_count = operation.to_bytes(1, "big")

    states_bytes_count = states.to_bytes(1, "big")

    username_bits = username.encode('utf-8')
    username_len = len(username_bits)
    usernamelen_bytes_count = username_len.to_bytes(4, "big")

    message_bits = message.encode('utf-8')
    message_len = len(message_bits)
    messagelen_bytes_count = message_len.to_bytes(4, "big")

    
    token_bits = token.encode('utf-8')
    token_len = len(token_bits)
    tokenlen_bytes_count = token_len.to_bytes(4,'big')

    return roomnamelen_bytes_count + operation_code_bytes_count + states_bytes_count + usernamelen_bytes_count + messagelen_bytes_count + tokenlen_bytes_count


def make_body(roomname, username, message):
    roomname_bits = roomname.encode('utf-8')
    username_bits = username.encode('utf-8')
    message_bits = message.encode('utf-8')
    return roomname_bits + username_bits + message_bits


def make_body_for_complite(roomname, username, message, token):
    roomname_encoded = roomname.encode('utf-8')
    username_encoded = username.encode('utf-8')
    message_encoded = message.encode('utf-8')
    token_encoded = token.encode('utf-8')

    return roomname_encoded + username_encoded + message_encoded + token_encoded


def is_roomname_registered(roomname):
    flag = False
    if roomname in rooms:
        flag = True
    return flag
    
def generate_token(length=32):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def add_roomname_to_rooms(roomname):
    with rooms_lock:
        rooms[roomname] = {}


def add_user_to_roomname(roomname, username):
    with rooms_lock:
        rooms[roomname][username] = {}
    

def add_token_to_user(roomname, username, token):
    with rooms_lock:
        rooms[roomname][username]["token"] = token


def add_address_to_username(roomname, username, addr):
    with rooms_lock:
        rooms[roomname][username]["address"] = addr


def add_last_time_sent_at_to_user(roomname, username):
    with rooms_lock:
        rooms[roomname][username]["last_time_sent_at"] = datetime.now()


def valid_token(roomname, token, client_addr):
    for userdata in rooms[roomname].values():
        if userdata.get("token") == token:
            if "udp_address" not in userdata:
                userdata["udp_address"] = client_addr
            return userdata.get("udp_address") == client_addr
    return False

def get_username(roomname, token):
    user_list = list(rooms[roomname].keys())
    for user in user_list:
        if rooms[roomname][user]["token"] == token:
            return str(user)
    return None


# def delete_client(sock:socket.socket) -> None:
#     while True:
#         i = 0
#         rooms_keys = list(rooms.keys()) # roomnameのリスト
#         for roomname in rooms_keys:
#             client_list = list(rooms[roomname].keys())
#             client_count = len(client_list)
#             print(f"現在の接続数：{client_count}")
#             for i in range(len(client_list)-1, -1, -1):
#                 last_time_sent_at = rooms[roomname][client_list[i]]["last_time_sent_at"]
#                 now = datetime.now()

#                 if now > last_time_sent_at + timedelta(seconds=30):
#                     # 削除したのがホストだったら。
#                     if i == 0:
#                         print(f"切断通知を送信します。")
#                         message = "ホストとの通信が途切れたので、このチャットルームを閉鎖します。"
#                         message_bits = message.encode("utf-8")
                        
#                         for user in client_list:
#                             sock.sendto(message_bits, user["address"])

#                         print(f"{roomname}を削除します")
#                         rooms.pop(roomname, None)
                    
#                     else:
#                         message = "参加者との通信が途絶えたので、参加者を退場させました。"
#                         message_bits = message.encode('utf-8')

#                         for user in client_list:
#                             sock.sendto(message_bits, user["address"])
                        
#                         print(f"{user}を削除します。")
#                         rooms[roomname].pop(user, None)



def handle_tcp_connection(client_socket, addr):
    
    print(f"接続が確立されました。{addr}")

    ##### クライアントからのリクエスト解析
    header = client_socket.recv(10)
    roomname_bytes_len = int.from_bytes(header[:4], "big")
    operation_code = int.from_bytes(header[4:5], "big")
    states = int.from_bytes(header[5:6], "big")
    username_bytes_len = int.from_bytes(header[6:10], "big")

    print(f"ルーム名のバイトの長さ：{roomname_bytes_len}")
    print(f"ユーザー名のバイトの長さ：{username_bytes_len}")

    body_len = roomname_bytes_len + username_bytes_len
    body = client_socket.recv(body_len)
    roomname = body[:roomname_bytes_len].decode('utf-8')
    username = body[roomname_bytes_len:].decode('utf-8')

    print(f"ルーム名：{roomname}")
    print(f"操作コード：{operation_code}")
    print(f"現在の状態：{states}")
    print(f"ユーザー名：{username}")


    ######　操作コード:1(作成), 状態：0 の時
    flag = True
    if operation_code == 1 and states == 0:
        flag = is_roomname_registered(roomname)
        token = generate_token()
        if not flag:
            add_roomname_to_rooms(roomname)
            add_user_to_roomname(roomname, username)
            add_token_to_user(roomname, username, token)

            ##### クライアントへ解析完了のメッセージ送信 state => 1:
            message = "チャットルーム作成(states = 0)のリクエストを受信し、解析しました。"
            states = 1
            print(message + "次の処理に進みます")

            header = make_header(roomname, operation_code, states, username, message)
            client_socket.sendall(header)

            body = make_body(roomname, username, message)
            client_socket.sendall(body)


            # roomname, username, operation_codeはそのまま使用する
            states = 2
            token = rooms[roomname][username]["token"]
            message = "サーバー側において、ルーム作成の処理は成功しました。"
            print(f"状態を2にして、トークンをクライアントに渡す処理に入ります。")

            header = make_header_for_complite(roomname, operation_code, states, username, message, token)
            client_socket.sendall(header)

            body = make_body_for_complite(roomname, username, message, token)
            client_socket.sendall(body)

            print("送信しました。")

            print(repr(addr))
            add_address_to_username(roomname, username, addr)

            client_ip = addr[0]
            ip_bits = client_ip.encode('utf-8')
            ip_bits_len = len(ip_bits)
            ip_bits_len_bits = ip_bits_len.to_bytes(1, "big")

            client_socket.sendall(ip_bits_len_bits)
            client_socket.sendall(ip_bits)

            client_port = addr[1]
            port_bits = client_port.to_bytes(2, "big")
            client_socket.sendall(port_bits)



            print("TCP通信のクライアントソケットを閉じました。")
            client_socket.close()


        else:
            message = "あなたのユーザー名ですでにチャットルームは作成されています。"
            retry_message_header = make_header(roomname, operation_code, states, username, message)
            client_socket.sendall(retry_message_header)

            retry_message_body = make_body(roomname, username, message)
            client_socket.sendall(retry_message_body)

    
    ######  操作コード：２(参加), 状態：0 の時
    elif operation_code == 2 and states == 0:
        flag = is_roomname_registered(roomname)
        if not flag:
            message = "存在しないチャットルームにアクセスしようとしています"
            retry_message_header = make_header(roomname, operation_code, states, username, message)
            client_socket.sendall(retry_message_header)

            retry_message_body = make_body(roomname, username, message)
            client_socket.sendall(retry_message_body)
        else :
            token = generate_token()
            add_user_to_roomname(roomname, username)
            add_token_to_user(roomname, username, token)

            ##### クライアントへ解析完了のメッセージ送信 state => 1:
            message = "チャットルームへの参加要求(states = 0)のリクエストを受信し、解析しました。"
            print(message + "次の処理に進みます。")
            states = 1
            header = make_header(roomname, operation_code, states, username, message)
            client_socket.sendall(header)
            body = make_body(roomname, username, message)

            ##### クライアントへ処理完了のメッセージ送信 state => 2:
            states = 2
            token = rooms[roomname][username]["token"]
            message = "サーバー側において、ルーム作成の処理は成功しました。"

            header = make_header_for_complite(roomname, operation_code, states, username, message, token)
            client_socket.sendall(header)
            body = make_body_for_complite(roomname, username, message, token)
            client_socket.sendall(body)


    
rooms = {}
rooms_lock = threading.Lock()

server_address = '127.0.0.1'
server_port = 9000

def main():
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    

    tcp_sock.bind((server_address, server_port))
    tcp_sock.listen(1)
    print("サーバー待機中……………………")

    tcp_thread = threading.Thread(target=tcp_listener, args=(tcp_sock,), daemon=True)
    tcp_thread.start()

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_thread = threading.Thread(target=udp_communication, args=(udp_sock,), daemon=True)
    udp_thread.start()

    threading.Event().wait()

    
def tcp_listener(sock):
    while True:
        try:
            client_socket, addr = sock.accept()
        except socket.error as err:
            print(err)
            break

        print(addr)
        tcp_thread = threading.Thread(target=handle_tcp_connection, args=(client_socket, addr), daemon=True)
        tcp_thread.start()

        
    

def udp_communication(sock):
    

    # thread_delete_client = threading.Thread(target=delete_client, args=(sock,), daemon=True)
    # thread_delete_client.start()


    while True:
        data, client_address = sock.recvfrom(4096)
        
        print(f"data received: {client_address}")

        roomname_size = int.from_bytes(data[:1], "big")
        token_size = int.from_bytes(data[1:2], "big")

        roomname = data[2:2+roomname_size].decode('utf-8')
        a = 2 + roomname_size
        token = data[a:a+token_size].decode('utf-8')

        b = a + token_size
        message = data[b:].decode('utf-8')

        print(f"ルーム名：{roomname}")
        print(f"トークン：{token}")
        print(f"メッセージ：{message}")

        is_valid = valid_token(roomname, token, client_address)
        username = get_username(roomname, token)

        print(is_valid)

        # 同チャットルーム内ですべてのクライアントにメッセージを送信
        if is_valid:
            add_last_time_sent_at_to_user(roomname, username)
            for userdata in rooms[roomname].values():
                addr = userdata["address"]
                message_bits = message.encode("utf-8")
                sock.sendto(message_bits, addr)
            
        else:
            print("トークンが有効ではないです。")
            token = ""


if __name__ == "__main__":
    main()