#!/bin/bash

echo `pwd`

search_string="$1"

for file in *
do
    if [ -f "$file" ]; then
        if grep -q "$search_string" "$file"; then
            echo "Found '$search_string' in file: $file"
        fi
    fi
done
