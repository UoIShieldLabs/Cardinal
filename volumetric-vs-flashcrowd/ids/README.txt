# IDS Container

dockerfile with suricata and tcpdump

## The two taps (T1 / T2)

This container sits between dmz_net (10.0.2.0/24) and protected_net
(10.0.3.0/24) with IP forwarding on, so every client<->app packet already
passes through its two NICs. That gives us both taps from the guide's
Figure 1 without a separate mirror port:

- T1 = the NIC on dmz_net -- traffic as it enters the edge segment, i.e.
  exactly what the IDS sensors see. Suricata and Zeek listen here only.
- T2 = the NIC on protected_net -- traffic as it actually reaches the
  application segment (nginx/app/db/cache), request and response both.

entrypoint.sh resolves each interface by subnet (not by assuming eth0/eth1,
which isn't guaranteed) and runs a rotating `tcpdump` on each one, writing
full-packet pcaps to `/pcaps/T1/` and `/pcaps/T2/` (5-minute files, last
hour kept). Everything here is passive: it reads a copy of the traffic and
never drops or blocks it.

To verify after `docker compose up`:

    docker exec -it ids bash -c "ps aux | grep tcpdump"
    docker exec -it ids bash -c "ls -la /pcaps/T1 /pcaps/T2"

Both should start filling in within the first capture window (~5 min, or
as soon as traffic flows). If one is empty, check the interface names
printed at container startup (`docker compose logs ids`) against the
awk-based resolution above.

## Requirements

- Docker-compatible runtime
  - Docker Desktop on Windows, or
  - Docker Engine in WSL/Linux/VM
- Linux containers enabled

## Folder Structure

```text
project-folder/
├── ids/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── rules/
│       ├── local.rules
│       └── syn_flood.zeek
├── logs/
└── pcaps/

## You will need to make the logs and pcaps folder on host machine.

## Open powershell, navigate to folder that contains your unzipped IDS folder.
	cd "$HOME\Downloads"

## Create Output Folders 
	mkdir logs
	mkdir pcaps

## Build Image
	docker build --progress=plain -t ids-test ".\ids"

## Name and Run Container
	docker run -it --name ids-container --cap-add NET_RAW --cap-add NET_ADMIN -v "${PWD}\logs:/logs" -v "${PWD}\pcaps:/pcaps" ids-test

## Check if running with 
	docker ps

## To get shell in container 
	docker exec -it ids-container bash

## In container, to check if IDS is running correctly
	ps aux | grep suricata
	ps aux | grep tcpdump
	ls /logs/suricata
	ls /pcaps

## To Exit 
	exit 
## or to exit in psh
	docker stop ids-container

## to start again later
	docker start ids-container
	docker exec -it ids-container bash

## TLDR
	mkdir logs
	mkdir pcaps
	docker build --progress=plain -t ids-test ".\ids"
	docker run -it --name ids-container --cap-add NET_RAW --cap-add NET_ADMIN -v "${PWD}\logs:/logs" -v "${PWD}\pcaps:/pcaps" ids-test

