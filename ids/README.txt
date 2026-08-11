# IDS Container

dockerfile with suricata and tcpdump

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

