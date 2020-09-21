# LiquidSecuritiesPOS
```
  _      _             _     _  _____                      _ _   _
 | |    (_)           (_)   | |/ ____|                    (_) | (_)
 | |     _  __ _ _   _ _  __| | (___   ___  ___ _   _ _ __ _| |_ _  ___  ___
 | |    | |/ _` | | | | |/ _` |\___ \ / _ \/ __| | | | '__| | __| |/ _ \/ __|
 | |____| | (_| | |_| | | (_| |____) |  __/ (__| |_| | |  | | |_| |  __/\__ \
 |______|_|\__, |\__,_|_|\__,_|_____/ \___|\___|\__,_|_|  |_|\__|_|\___||___/
              | |
              |_|    Demo Liquid POS

 This is an examples of POS terminal using GDK, python and M5Stack board.
             DON'T USE THIS CODE IN PRODUCTION
```

M5stack based POS for Liquid Securities tokens.

- http.server is not ready for a production service
- we don't show how to add a tls certificate
- configurations and mnemonic are saved in the same file in plain text
- we use error messages in json without specific codes
- connection status is not monitored
- printer is not monitored
- payments request are persisted in a local file
- communication is not encrypted
- messages are not signed
- there is not an authentication phase  

## Install the backend
In a python3 virtual environment install GDK (https://github.com/Blockstream/gdk/releases).

Run the script adding the port number as argument.

`python pos_backend.py 80`

### Available commands

- `/status` return always a static message
- `/assets` return the list of accepted assets
- `/gaid` return Liquid Securities account GAID
- `/balance` return the balance of subaccount, if `asset` argument is passed return the balance of the selected asset, if not pass the list of known assets
- `/check` check if a payment is performed if the argument `pointer` is passed (and print information using the thermal printer) or return the list of payment requests
- `/address` return an address an save request payment (`name`, `asset`, `amount` arguments can be passed on url)
- `/summary` print the payment request summary on the thermal printer

## Install the firmware
Open `m5green.ino` using Arduino IDE, configure the firmware using your IP and port number.
