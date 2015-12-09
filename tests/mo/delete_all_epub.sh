#!/bin/bash

for DIR in epub*
do
    cd $DIR
    EPUB_FILE="$DIR"".epub"
    rm -f $EPUB_FILE
    echo "[INFO] Deleted $EPUB_FILE"
    cd ..
done
