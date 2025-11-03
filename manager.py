# manager.py (Version 3 - Scheduled Restart)
# A Python-based watchdog to run and restart the Hypercorn server daily at a specific time.

import subprocess
import time
import sys
import datetime

# --- Configuration ---
# The command to run your server, broken into a list of arguments.
COMMAND = [
    sys.executable,
    "-m", "hypercorn",
    "wsgi:application",
    "--bind", "0.0.0.0:8085",
    "--certfile", r"D:\certs\7db886ac63f4bfb8.pem",
    "--keyfile", r"D:\certs\privateKey.key"
]

# The specific time of day to restart the server.
RESTART_HOUR = 1  # 1 AM
RESTART_MINUTE = 0

def get_seconds_until_next_restart():
    """
    Calculates the number of seconds from now until the next scheduled restart time.
    """
    now = datetime.datetime.now()
    # Set the target restart time for today.
    restart_time_today = now.replace(hour=RESTART_HOUR, minute=RESTART_MINUTE, second=0, microsecond=0)

    # If the current time is already past today's restart time,
    # the next restart must be tomorrow.
    if now >= restart_time_today:
        next_restart_time = restart_time_today + datetime.timedelta(days=1)
    else:
        next_restart_time = restart_time_today

    # Calculate the difference in seconds.
    seconds_to_wait = (next_restart_time - now).total_seconds()
    
    # Convert timedelta to a readable format for logging.
    hours, remainder = divmod(seconds_to_wait, 3600)
    minutes, _ = divmod(remainder, 60)
    
    print(f"MANAGER: Current time is {now.strftime('%Y-%m-%d %H:%M:%S')}.")
    print(f"MANAGER: Next restart is scheduled for {next_restart_time.strftime('%Y-%m-%d %H:%M:%S')}.")
    print(f"MANAGER: Waiting for {int(hours)} hours and {int(minutes)} minutes.")
    
    return seconds_to_wait

def run_server():
    """
    Starts the server as a subprocess and monitors it for scheduled restarts.
    """
    while True:
        print(f"\nMANAGER: Starting Hypercorn server process...")
        try:
            # Start the Hypercorn server as a child process.
            server_process = subprocess.Popen(COMMAND)

            # Calculate and wait for the time until the next restart.
            seconds_until_restart = get_seconds_until_next_restart()
            time.sleep(seconds_until_restart)

            # Gracefully terminate the process and wait for it to exit.
            print("\nMANAGER: Scheduled restart time reached. Gracefully shutting down server...")
            server_process.terminate()
            server_process.wait(timeout=30) # Wait up to 30 seconds.
            print("MANAGER: Server shut down. Restarting immediately...")

        except subprocess.TimeoutExpired:
            print("MANAGER: Server did not shut down gracefully. Forcing termination.")
            server_process.kill()
        except KeyboardInterrupt:
            print("MANAGER: Manual shutdown detected. Stopping server...")
            server_process.terminate()
            server_process.wait()
            break # Exit the while loop
        except Exception as e:
            print(f"MANAGER: An unexpected error occurred: {e}")

if __name__ == "__main__":
    run_server()