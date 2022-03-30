import random
import subprocess
import base64

def print_banner() -> None:
    print("""
             _   _                         _            _ _                 
 _ __  _   _| |_| |__   ___  _ __    _ __ (_)_ __   ___| (_)_ __   ___  ___ 
| '_ \| | | | __| '_ \ / _ \| '_ \  | '_ \| | '_ \ / _ \ | | '_ \ / _ \/ __|
| |_) | |_| | |_| | | | (_) | | | | | |_) | | |_) |  __/ | | | | |  __/\__ \\
| .__/ \__, |\__|_| |_|\___/|_| |_| | .__/|_| .__/ \___|_|_|_| |_|\___||___/
|_|    |___/                        |_|     |_|                            
    """, flush=True)

def generate_random_string(length: int) -> str:
    random_string = ''
    
    for _ in range(length):
        random_1 = random.randint(48, 57) # take a one number between 0-9
        # random_2 = random.randint(65, 90) # take a one number between A-Z
        random_3 = random.randint(97, 122) # take a one number between a-z

        random_select = random.randint(0,1)

        random_integer = [random_1, random_3][random_select]
        # Keep appending random characters using chr(x)
        random_string += (chr(random_integer))
    
    return random_string

def encode_str_to_base64(string: str) -> str:
    return base64.b64encode(bytes(string, 'utf-8')).decode("utf-8")

def decode_base64_to_str(base64_content: bytes) -> str:
    return base64.b64decode(base64_content).decode("utf-8")

def exec(command: str):
        result = subprocess.run(command.split(), stdout=subprocess.PIPE)
        return (result.stdout.decode('utf8'), result.returncode)