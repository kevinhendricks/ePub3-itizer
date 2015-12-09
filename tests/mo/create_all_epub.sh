#!/bin/bash

for DIR in epub*
do
    cd $DIR
    if [ -e "$DIR" ]
    then
        EPUB_FILE="$DIR"".epub"
        rm -f $EPUB_FILE
        cd $DIR
        zip -DX0 $EPUB_FILE "mimetype" > /dev/null
        zip -DrX9 $EPUB_FILE "META-INF" > /dev/null
        zip -DrX9 $EPUB_FILE "OEBPS" > /dev/null
        mv $EPUB_FILE ..
        echo "[INFO] Created $EPUB_FILE"
        cd ..
    fi
    cd ..
done
