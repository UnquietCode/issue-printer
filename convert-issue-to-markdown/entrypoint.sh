#!/bin/sh -l
set -x

CONTENT=$1
CONTENT_64=$2
CONTENT_URL=$3

INPUT_JSON=$(mktemp)

if [ -z "$CONTENT" ]; then
  echo "$CONTENT" > "$INPUT_JSON"
elif [ -z "$CONTENT_64" ]; then
  echo "$CONTENT_64" | base64 -d > "$INPUT_JSON"
elif [ -z "$CONTENT_URL" ]; then
  curl "$CONTENT_URL" -o "$INPUT_JSON"
else
  echo "either content, encoded content, or content URL must be provided"
  echo "usage: (content) (content base 64) (content URL)"
  exit 1
fi

$OUTPUT_ZIP=$(mktemp)
python3 /app/run.py "$INPUT_JSON" "$OUTPUT_ZIP"

echo "::set-output name=zip_data::$(base64 "$OUTPUT_ZIP")"