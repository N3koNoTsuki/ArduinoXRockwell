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
sserveur.listen(1)
sserveur.settimeout(0.1)

sclient = None
adclient = None

print("Serveur lancé")

Bridge.provide("linux_started", linux_started)
Bridge.provide("python_func", python_func)

print("Hello WebUI")
ui = WebUI()
ui.expose_api("GET", "/hello", lambda: {"message": "initialisation"})


def handle_message(decoded: str) -> str | None:
    message = decoded.strip()

    print(f"Message reçu : {message!r}")

    if message == "temp":
        if Meteo.temp is not None:
            ui.send_message("temp", Meteo.temp)
            nl.print_meteo(Meteo, False)
            return f"{Meteo.temp}"
        return "temp indisponible"

    return f"{len(message)} octets"


def loop():
    global sclient, adclient

    # 1) Accepter un client seulement si aucun n'est connecté
    if sclient is None:
        try:
            client, addr = sserveur.accept()
            client.settimeout(0.1)
            sclient = client
            adclient = addr
            print(f"Connecté : {adclient}")
        except socket.timeout:
            return

    # 2) Lire le client courant
    try:
        donnees = sclient.recv(4096)

        if not donnees:
            print("[Client déconnecté]")
            sclient.close()
            sclient = None
            adclient = None
            return

        decoded = donnees.decode(errors="replace")

        reponse = handle_message(decoded)
        if reponse is not None:
            sclient.sendall(reponse.encode())

    except socket.timeout:
        # Rien reçu sur cette itération, on laisse App.run rappeler loop()
        return

    except ConnectionResetError:
        print("[Connexion reset par client]")
        sclient.close()
        sclient = None
        adclient = None
        return

    except EOFError:
        print("[EOF client]")
        sclient.close()
        sclient = None
        adclient = None
        return

    except Exception as e:
        print(f"[Erreur] {e}")
        if sclient is not None:
            sclient.close()
            sclient = None
            adclient = None


App.run(user_loop=loop)
