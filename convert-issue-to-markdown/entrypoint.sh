#!/bin/sh -l
set -e

export GITHUB_TOKEN="$1"
CONTENT="$2"
CONTENT_64="$3"
CONTENT_URL="$4"

INPUT_JSON=$(mktemp tmpXXXXXX.json)

if [ -n "$CONTENT" ]; then
  echo "$CONTENT" > "$INPUT_JSON"
elif [ -n "$CONTENT_64" ]; then
  echo "$CONTENT_64" | base64 -d > "$INPUT_JSON"
elif [ -n "$CONTENT_URL" ]; then
  curl "$CONTENT_URL" -o "$INPUT_JSON"
else
  echo "either content, encoded content, or content URL must be provided"
  echo "usage: (content) (content base 64) (content URL)"
  exit 1
fi

OUTPUT_ZIP=$(mktemp tmpXXXXXX.zip)
python3 /app/run.py "$INPUT_JSON" "$OUTPUT_ZIP"

echo "::set-output name=zip_data::$(base64 -w0 "$OUTPUT_ZIP")"