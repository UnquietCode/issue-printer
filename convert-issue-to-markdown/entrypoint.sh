#!/bin/sh -l
set -x

CONTENT=$1
CONTENT_64=$2

INPUT_JSON=$(mktemp)

if [ -z "$CONTENT" ]; then
  echo "$CONTENT" > "$INPUT_JSON"
elif [ -z "$CONTENT_64" ]; then
  echo "$CONTENT_64" | base64 -d > "$INPUT_JSON"
else
  echo "either content or encoded content must be provided"
  echo "usage: (content) (content base 64)"
  exit(1)
fi

OUTPUT_MARKDOWN=$(mktemp)
python3 /app/run.py "$INPUT_JSON" "$OUTPUT_MARKDOWN"

echo "::set-output name=markdown::$(base64 "$OUTPUT_MARKDOWN")"