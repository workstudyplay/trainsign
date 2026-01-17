#!/bin/bash

cd ui
npm run build
scp -r dist/* pi@mysign.local:~/trainsign/ui/dist/

cd ..

scp -r src/ pi@mysign.local:~/trainsign/src/
