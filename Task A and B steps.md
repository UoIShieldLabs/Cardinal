### What I added for task C

#### L4 - updated generated traffic

Created in *flash-crowd* folder

|

|-> locustfile.py

updated in *flash-crowd* folder

|

|-> dockerfile, ramp.sh

#### Nginx - reverse proxy

Created in *victim* folder

|

|-> Nginx.conf



Updated in *victim* folder

|

|-> dockerfile

### what I added for Task A and B

created *app* folder
|
|->app.py, dockerfile, requirements.txt



Updated *docker-compose.yml*

* added db:, and cache:, app: to yaml



created *db-init* folder

|

|-> init.sql



### Steps in TASK A video

1. docker compose up -d --build db cache app
2. docker compose logs app
3. (Invoke-WebRequest -Uri "http://localhost:5000/product/1" -UseBasicParsing).Content

   1. repeat if you want to see expensive vs cheap
4. Invoke-RestMethod -Uri "http://localhost:5000/checkout" -Method Post -Headers @{"X-Session-ID"="test-session-123"} -ContentType "application/json" -Body '{"product": 1}'
5. docker exec -it shop\_db psql -U shopuser -d shopdb -c "SELECT \* FROM orders;”



### explanation

1. Docker builds db, cache, and app that were added in the docker-compose.yml file
2. This will show recent console output directly from the python app. I was just using this to verify the web app booted up okay and was listening
3. the first this is sent it will be expensive as it is not cached by Redis. However, anytime after this it should return with <!-- CACHE: HIT -->
4. this is simulating a user checking out. This is done by sending a POST request containing a JSON payload and a custom session ID. It triggers the backend app logic to write a new order which is then recorded **in the DB**
5. This last step is to check the PostgreSQL container by using a SQL query to display an existing data in the order table.

