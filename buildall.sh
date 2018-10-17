#!/bin/bash

cd doc
make clean
make html
make latexpdf
cd _build
tar -zcvf FIXGateway-html.tar.gz html
cd ../..
