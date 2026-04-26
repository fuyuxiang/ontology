#!/bin/bash
cd "$(dirname "$0")"
echo "Restarting services..."
./stop.sh
echo
./start.sh
