#!/bin/bash
echo "Stopping services..."

cd "$(dirname "$0")"

if [ -f .backend.pid ]; then
    kill "$(cat .backend.pid)" 2>/dev/null
    rm -f .backend.pid
    echo "  Backend stopped."
fi

if [ -f .frontend.pid ]; then
    kill "$(cat .frontend.pid)" 2>/dev/null
    rm -f .frontend.pid
    echo "  Frontend stopped."
fi

echo "Done."
