#!/bin/bash

set -e

echo "Waiting 200 seconds to allow Elastic Beanstalk deployment to settle..."
sleep 120

# Get current branch name
BRANCH_NAME=${GITHUB_HEAD_REF:-${GITHUB_REF##*/}}

# Fetch Beanstalk environment CNAME (URL)
APP_URL=https://ilmath.ilmino.com

# Get Elastic Beanstalk health
HEALTH=$(aws elasticbeanstalk describe-environments \
  --environment-names "$EB_ENV_NAME" \
  --query "Environments[0].Health" \
  --output text 2>/dev/null) || HEALTH="UNKNOWN"

# Get HTTP status response
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "http://ilm-math-ai.eu-west-2.elasticbeanstalk.com/") || HTTP="000"

# Get deployer info
DEPLOYER=${GITHUB_TRIGGERING_ACTOR:-$GITHUB_ACTOR}

# Send Slack message
MESSAGE="*CI/CD Pipeline Status*: $1\n*Branch*: $BRANCH_NAME\n*Deployed by*: $DEPLOYER\n*Elastic Beanstalk Health*: $HEALTH\n*HTTP Status*: $HTTP\n*App*: $EB_APP_NAME\n*Env*: $EB_ENV_NAME\n*URL*: $APP_URL"

curl -X POST -H 'Content-type: application/json' \
     --data "{\"text\":\"$MESSAGE\"}" "$SLACK_WEBHOOK_URL" || echo "Slack notification failed, continuing..."
