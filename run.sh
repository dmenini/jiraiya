#!/bin/bash

project_path="$1"

if [ -z "$project_path" ]; then
    echo "Error: Missing required parameter (path to project main module)."
    exit 1
fi

if [ ! "$AWS_DEFAULT_REGION" ]; then
  export AWS_DEFAULT_REGION=eu-central-1
  echo "No AWS_DEFAULT_REGION set, will use default: $AWS_DEFAULT_REGION"
fi

if [[ -z "$AWS_ACCESS_KEY_ID" ]]; then
  echo 'Please define AWS_ACCESS_KEY_ID in your environment variables.'
  exit 1
fi

if [[ -z "$AWS_SECRET_ACCESS_KEY" ]]; then
  echo 'Please define AWS_SECRET_ACCESS_KEY in your environment variables.'
  exit 1
fi

if [[ -z "$AWS_SESSION_TOKEN" ]]; then
  echo 'Please define AWS_SESSION_TOKEN in your environment variables.'
  exit 1
fi

PYTHONPATH="." streamlit run jiraiya/app.py
