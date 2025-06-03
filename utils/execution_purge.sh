#!/bin/bash

# Capture the output of rto ls
directories=$(rto ls | grep "tool_exec-" | grep "/" | sed 's/\/$//')

# Loop through each directory and delete it
for dir in $directories; do
  echo "Deleting $dir"
  rto rm -rf "$dir"
done

echo "All tool_exec directories have been removed."
