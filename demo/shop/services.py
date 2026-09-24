from repository import find_user
import subprocess

def get_user(user_id: str):
    return find_user(user_id)

def run_diagnostic(host: str):
    command = "ping -c 1 " + host
    return subprocess.check_output(command, shell=True)
