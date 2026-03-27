import socket
import time
import neko_no_lib as nl
from arduino.app_utils import *
from arduino.app_bricks.web_ui import WebUI

Grenoble = nl.City(name="Grenoble", lat=45.18, lon=5.72)
Meteo = nl.Meteo(temp=0.0, location=Grenoble)


def linux_started():
    return True


def python_func(data: float):
    global Meteo
    Meteo.temp = data


sserveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sserveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sserveur.bind(("0.0.0.0", 5010))
sserveur.listen(5)
sserveur.settimeout(0.0)  # accept non bloquant

sclient = None
adclient = None

print("Serveur lancé")

Bridge.provide("linux_started", linux_started)
Bridge.provide("python_func", python_func)

print("Hello WebUI")
ui = WebUI()
ui.expose_api("GET", "/hello", lambda: {"message": "initialisation"})


def close_client():
    global sclient, adclient

    if sclient is not None:
        try:
            sclient.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass

        try:
            sclient.close()
        except Exception:
            pass

    sclient = None
    adclient = None


def handle_message(decoded: str) -> str | None:
    message = decoded.strip()

    print(f"Message reçu : {message!r}")

    if message == "big":
        return (
            "Dans un système embarqué, la transmission de données repose sur des "
            "trames structurées permettant d’assurer la synchronisation, l’intégrité "
            "et l’interprétation correcte des informations. Chaque trame est "
            "généralement composée d’un en-tête contenant des métadonnées, suivi "
            "d’un champ de données utile appelé payload, puis d’un champ de contrôle "
            "comme un CRC ou checksum. La taille des trames peut varier selon le "
            "protocole utilisé, mais elle doit rester adaptée aux contraintes du "
            "réseau, notamment en termes de bande passante et de latence. Une trame "
            "trop longue peut augmenter le risque d’erreurs, tandis qu’une trame trop "
            "courte peut réduire l’efficacité globale de la communication. Dans les "
            "systèmes industriels, comme ceux utilisant Ethernet/IP ou Modbus, la "
            "gestion des trames est essentielle pour garantir un échange fiable entre "
            "les automates programmables et les équipements connectés."
            "NKP2"
        )

    if message == "temp":
        if Meteo.temp is not None:
            ui.send_message("temp", Meteo.temp)
            nl.print_meteo(Meteo, False)
            return f"{Meteo.temp}NKP2"
        return "temp indisponible"

    return f"{len(message)} octetsNKP2"


def recv_exact(sock, size: int) -> bytes:
    data = b""

    while len(data) < size:
        chunk = sock.recv(size - len(data))

        if chunk == b"":
            raise ConnectionResetError("Connexion fermée proprement par le client")

        data += chunk

    return data


def send_frame(sock, payload: str):
    payload_bytes = payload.encode()
    header = f"NKP1{len(payload_bytes):04d}".encode()
    sock.sendall(header)
    sock.sendall(payload_bytes)


def accept_new_client_if_any():
    global sclient, adclient

    while True:
        try:
            client, addr = sserveur.accept()
            client.settimeout(1.0)

            print(f"Nouveau client détecté : {addr}")

            if sclient is not None:
                print(f"Remplacement de l'ancien client : {adclient}")
                close_client()

            sclient = client
            adclient = addr
            print(f"Client actif : {adclient}")

        except BlockingIOError:
            break
        except Exception as e:
            print(f"[Erreur accept] {e}")
            break


def loop():
    global sclient, adclient

    accept_new_client_if_any()

    if sclient is None:
        return

    try:
        header = recv_exact(sclient, 8)
        print(f"Header brut : {header!r}")

        signature = header[:4].decode(errors="replace")
        size_str = header[4:8].decode(errors="replace")

        if signature != "NKP1":
            print(f"[Header invalide] Signature reçue : {signature!r}")
            send_frame(sclient, "ERR_SIGNATURE")
            return

        if not size_str.isdigit():
            print(f"[Header invalide] Taille non numérique : {size_str!r}")
            send_frame(sclient, "ERR_SIZE_FORMAT")
            return

        payload_size = int(size_str)
        print(f"Taille payload annoncée : {payload_size}")

        if payload_size < 0:
            print("[Header invalide] Taille négative")
            send_frame(sclient, "ERR_SIZE_VALUE")
            return

        payload_bytes = recv_exact(sclient, payload_size)

        if len(payload_bytes) != payload_size:
            print(
                f"[Payload invalide] attendu={payload_size}, reçu={len(payload_bytes)}"
            )
            send_frame(sclient, "ERR_PAYLOAD_SIZE")
            return

        decoded_payload = payload_bytes.decode(errors="replace")
        print(f"Payload reçu : {decoded_payload!r}")

        if len(decoded_payload) < 4:
            print("[Payload invalide] trop court pour contenir NKP2")
            send_frame(sclient, "ERR_SIGNATURE")
            return

        payload = decoded_payload[:-4]
        footer = decoded_payload[-4:]

        if footer != "NKP2":
            print(f"[Footer invalide] Signature reçue : {footer!r}")
            send_frame(sclient, "ERR_SIGNATURE")
            return

        response = handle_message(payload)
        if response is not None:
            send_frame(sclient, response)

    except socket.timeout:
        return

    except (ConnectionResetError, BrokenPipeError):
        print("[Client déconnecté]")
        close_client()
        return

    except EOFError:
        print("[EOF client]")
        close_client()
        return

    except Exception as e:
        print(f"[Erreur] {e}")
        close_client()


App.run(user_loop=loop)
