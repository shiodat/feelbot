#!/bin/bash
docker run --name feelbot -p 8000:80 --env-file /home/ubuntu/.env feelbot 
