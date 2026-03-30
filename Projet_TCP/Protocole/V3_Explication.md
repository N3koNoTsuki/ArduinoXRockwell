# Explication relative au SFC de la V3

`../Rockwell/src/V3.ACD`

## Vue globale

Le système est organisé autour d’un SFC structuré en plusieurs états permettant :
- l’initialisation de la communication
- l’envoi d’une requête
- la réception et le traitement d’une trame
- la gestion des erreurs et resynchronisation

#### Vue global du SFC

![SFC Overview](img_V3/SFC_V3_1.png "SFC_1")
![SFC Overview](img_V3/SFC_V3_2.png "SFC_2")
![SFC Overview](img_V3/SFC_V3_3.png "SFC_3")
![SFC Overview](img_V3/SFC_V3_4.png "SFC_4")

---

## Séquence principale

### 1. INIT
Initialisation complète du système :
- Reset des erreurs
- Initialisation socket (création + ouverture connexion)

Transition :
- Si `Init_Done` → passage en `IDLE`
- Si erreur → retour `RESET_ALL`

---

### 2. IDLE
État d’attente :
- Aucune action
- Surveillance d’une demande utilisateur

Transition :
- Si `Request_to_send` → passage en `WRITE`

---

### 3. WRITE
Construction et envoi de la requête :
- Génération du header `NKP1XXXX` basé sur la taille du payload
- Envoi du header puis du payload

Transition :
- Si écriture terminée (`Write_Done`) → `WAIT_DATA`

---

### 4. WAIT_DATA
Attente de données entrantes via socket

Comportement :
- Lecture du buffer
- Comptage des tentatives de lecture

Transitions :
- Si données reçues → `APPEND_DATA`
- Si aucune donnée après 3 lectures → retour `IDLE`

---

### 5. APPEND_DATA
Accumulation des données reçues dans le buffer global

Transition :
- Toujours → `FIND_HEADER`

---

### 6. FIND_HEADER
Recherche du header dans le buffer (`NKP1`)

Cas possibles :
- Header trouvé en position 0 → `WAIT_HEADER`
- Header trouvé mais décalé → `CLEAN_BUFFER`
- Header non trouvé → retour lecture (`WAIT_DATA`)

---

### 7. CLEAN_BUFFER
Recalage du buffer :
- Suppression des données avant le header

Transition :
- Une fois fait → `WAIT_HEADER`

---

### 8. WAIT_HEADER
Attente d’un header complet (taille suffisante)

Transition :
- Si `Rx_Count >= 8` → `CHECK_HEADER`
- Sinon → retour `WAIT_DATA`

---

### 9. CHECK_HEADER
Validation du header :
- Vérification signature `NKP1`
- Extraction taille payload
- Vérification cohérence

Transitions :
- Si invalide → `RESYNC`
- Si valide → `WAIT_FRAME`

---

### 10. WAIT_FRAME
Attente de la trame complète (header + payload + footer)

Transition :
- Si taille complète reçue → `PROCESS`
- Sinon → retour `WAIT_DATA`

---

### 11. PROCESS
Traitement de la trame :
- Vérification du footer
- Extraction du payload
- Mise à jour des données (`Rx_Update`)

Transitions :
- Si données traitées → retour `IDLE`
- Si erreur footer → `RESYNC`

---

### 12. RESYNC
Resynchronisation du flux :
- Vidage du buffer
- Réinitialisation des variables de réception

Transition :
- Retour vers `WAIT_DATA`

---
