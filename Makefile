TAG=local
RPC_NODE=https://rpc-osmosis.blockapsis.com/
CHECK_INTERVAL=10

start:
	RPC_NODE=$(RPC_NODE) uvicorn main:app --reload --host 0.0.0.0 --port 8080

build:
	docker build -t rpc-sync-controller:$(TAG) .

run:
	docker run -p 8080:8080 -e RPC_NODE=$(RPC_NODE) -e CHECK_INTERVAL=$(CHECK_INTERVAL) --name rpc-sync-controller rpc-sync-controller:$(TAG) 

rund:
	docker run -d -p 8080:8080 -e RPC_NODE=$(RPC_NODE) -e CHECK_INTERVAL=$(CHECK_INTERVAL) --name rpc-sync-controller rpc-sync-controller:$(TAG) 

exec:
	docker run -p 8080:8080 -e RPC_NODE=$(RPC_NODE) -e CHECK_INTERVAL=$(CHECK_INTERVAL) --name rpc-sync-controller -ti --entrypoint bash rpc-sync-controller:$(TAG) 

stop: 
	docker stop -t 0 rpc-sync-controller

remove: stop
	docker rm rpc-sync-controller
