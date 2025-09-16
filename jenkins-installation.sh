#!/bin/bash

echo "1. Updating"
sudo apt update

echo "1. Installing openjdk-21"
sudo apt install -y openjdk-17-jdk

echo "3. Adding jenkins pakage to apt list"
sudo wget -O /etc/apt/keyrings/jenkins-keyring.asc \
  https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key
echo "deb [signed-by=/etc/apt/keyrings/jenkins-keyring.asc]" \
  https://pkg.jenkins.io/debian-stable binary/ | sudo tee \
  /etc/apt/sources.list.d/jenkins.list > /dev/null

echo "4. Updating apt and installing Jenkins"
sudo apt-get update
sudo apt-get install jenkins